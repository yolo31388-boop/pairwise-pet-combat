"""宠物出战与技能循环系统"""
from dataclasses import dataclass, field

# 战斗常量
SWITCH_CD = 5.0            # 出战切换冷却（秒）
MAX_SWITCHES = 3           # 单场战斗切换次数上限
SWITCH_INVINCIBLE = 1.0    # 切换后短暂无敌（秒）
GCD = 1.5                  # 公共冷却（秒）
NEW_PET_HP_RATIO = 0.8     # 新宠物出战血量继承比例
ENERGY_REGEN = 20          # 每回合能量回复（普攻积攒）
MAX_ENERGY = 100
LOW_HP_THRESHOLD = 0.3     # 残血阈值


@dataclass
class PetSkill:
    sid: str
    name: str
    damage: float
    energy_cost: int = 0
    cooldown: float = 0
    priority: int = 1


@dataclass
class BattlePet:
    pid: str
    name: str
    hp: float = 100
    energy: int = 100
    skills: list[PetSkill] = field(default_factory=list)
    passive: dict = field(default_factory=dict)


class PetBattle:
    def __init__(self):
        self.pets: dict[str, BattlePet] = {}
        self.active_pet: str = ""
        self.switch_cd: float = SWITCH_CD
        self.last_switch_time: float = 0.0
        self.switch_count: int = 0
        self.invincible_until: float = 0.0
        self.last_gcd_time: float = -float("inf")
        self.skill_last_used: dict[str, float] = {}

    # bug1: 切换有冷却、有次数限制，切换后短暂无敌
    def switch_pet(self, pet_id: str, current_time: float) -> bool:
        if current_time - self.last_switch_time < self.switch_cd:
            return False
        if self.switch_count >= MAX_SWITCHES:
            return False
        self.active_pet = pet_id
        self.last_switch_time = current_time
        self.switch_count += 1
        self.invincible_until = current_time + SWITCH_INVINCIBLE
        return True

    def is_invincible(self, current_time: float) -> bool:
        return current_time < self.invincible_until

    # bug2: 技能优先级按目标状态（血量/类型/距离）动态计算
    def select_skill(self, pet: BattlePet, target_hp: float,
                     target_type: str, target_dist: float = 1.0) -> PetSkill:
        best, best_score = None, -float("inf")
        for skill in pet.skills:
            score = skill.priority * 10 + skill.damage
            # 残血目标优先高伤害终结技
            if target_hp <= LOW_HP_THRESHOLD * 100:
                score += skill.damage * 2
            # 高血量目标优先低耗技能打消耗
            else:
                score -= skill.energy_cost
            # 距离远时惩罚近战高耗技能
            score -= skill.energy_cost * target_dist * 0.1
            if score > best_score:
                best, best_score = skill, score
        return best

    # bug3: AI 目标选择，优先威胁值高或残血目标；治疗宠优先奶最低血量友方
    def select_target(self, pet: BattlePet, enemies: list) -> str:
        if not enemies:
            return ""
        def threat(e):
            hp = e.get("hp", 100)
            t = e.get("threat", 0)
            score = t
            if hp <= LOW_HP_THRESHOLD * 100:
                score += 100 - hp  # 残血优先收割
            return score
        return max(enemies, key=threat).get("id", "")

    def select_heal_target(self, pet: BattlePet, allies: list) -> str:
        if not allies:
            return ""
        return min(allies, key=lambda a: a.get("hp", 100)).get("id", "")

    # bug4: 技能有 GCD 和独立冷却，不能同时释放
    def get_gcd(self) -> float:
        return GCD

    def can_cast(self, skill: PetSkill, pet: BattlePet, current_time: float) -> bool:
        if current_time - self.last_gcd_time < GCD:
            return False
        if current_time - self.skill_last_used.get(skill.sid, -float("inf")) < skill.cooldown:
            return False
        if pet.energy < skill.energy_cost:
            return False
        return True

    def cast_skill(self, skill: PetSkill, pet: BattlePet, current_time: float) -> bool:
        if not self.can_cast(skill, pet, current_time):
            return False
        pet.energy -= skill.energy_cost
        self.last_gcd_time = current_time
        self.skill_last_used[skill.sid] = current_time
        return True

    # bug5: 新宠物出战血量按比例继承，有递减惩罚
    def get_new_pet_hp(self, pet: BattlePet) -> float:
        return pet.hp * NEW_PET_HP_RATIO

    # bug6: 能量/怒气限制：普攻积攒，大招耗能量，不能无限放
    def get_energy_regen(self, pet: BattlePet) -> int:
        return min(pet.energy + ENERGY_REGEN, MAX_ENERGY)

    # bug7: 多只宠物被动叠加：同名被动取最高值，不同名被动全部生效
    def get_passive_stacking(self, pets: list[BattlePet]) -> dict:
        result: dict = {}
        for pet in pets:
            for key, value in pet.passive.items():
                if key not in result or value > result[key]:
                    result[key] = value
        return result
