"""宠物出战与技能循环系统"""
from dataclasses import dataclass, field

# 战斗常量
SWITCH_CD = 5.0                # 出战切换冷却(秒)
MAX_SWITCHES_PER_BATTLE = 5    # 单场战斗切换次数上限
SWITCH_INVINCIBLE_TIME = 1.0   # 切换后短暂无敌(秒)
GCD = 1.5                      # 公共冷却(秒)
NEW_PET_HP_RATIO = 0.8         # 新宠物入场血量继承比例
ENTRY_HP_PENALTY = 0.1         # 每次换宠的额外血量递减惩罚
ENERGY_REGEN_PER_TURN = 20     # 每回合能量回复
MAX_ENERGY = 100
ULT_ENERGY_COST = 100          # 大招需要满能量
LOW_HP_THRESHOLD = 0.3         # 残血判定阈值(按目标血量绝对值近似)


@dataclass
class PetSkill:
    sid: str
    name: str
    damage: float
    energy_cost: int = 0
    cooldown: float = 0
    priority: int = 1
    # 独立冷却的就绪时间,由战斗进程维护
    ready_time: float = 0.0


@dataclass
class BattlePet:
    pid: str
    name: str
    hp: float = 100
    energy: int = 100
    skills: list[PetSkill] = field(default_factory=list)
    passive: dict = field(default_factory=dict)
    role: str = "dps"  # dps / healer / tank


class PetBattle:
    def __init__(self):
        self.pets: dict[str, BattlePet] = {}
        self.active_pet: str = ""
        self.switch_cd: float = SWITCH_CD
        self.last_switch_time: float = 0.0
        self.switch_count: int = 0
        self.invincible_until: float = 0.0
        self.last_gcd_time: float = -float("inf")

    # ---- bug1: 切换冷却 + 次数限制 + 切换后短暂无敌 ----
    def switch_pet(self, pet_id: str, current_time: float) -> bool:
        if current_time - self.last_switch_time < self.switch_cd:
            return False
        if self.switch_count >= MAX_SWITCHES_PER_BATTLE:
            return False
        self.active_pet = pet_id
        self.last_switch_time = current_time
        self.switch_count += 1
        self.invincible_until = current_time + SWITCH_INVINCIBLE_TIME
        return True

    def is_invincible(self, current_time: float) -> bool:
        return current_time < self.invincible_until

    # ---- bug2: 技能优先级按目标状态动态计算 ----
    def select_skill(self, pet: BattlePet, target_hp: float,
                     target_type: str = "normal", target_distance: float = 0.0,
                     current_time: float = 0.0) -> PetSkill:
        usable = [s for s in pet.skills
                  if s.energy_cost <= pet.energy and s.ready_time <= current_time]
        if not usable:
            usable = list(pet.skills)
        def score(skill: PetSkill) -> float:
            s = skill.priority * 10.0
            # 目标残血:优先高伤害终结技
            if target_hp <= LOW_HP_THRESHOLD * 100:
                s += skill.damage
            # 精英/boss 目标:优先高伤害技能
            if target_type in ("elite", "boss"):
                s += skill.damage * 0.5
            # 能量不足时偏向低耗技能
            if skill.energy_cost > pet.energy:
                s -= 1000
            return s
        return max(usable, key=score)

    # ---- bug3: 目标选择:威胁值/残血优先;治疗宠奶最低血量友方 ----
    def select_target(self, pet: BattlePet, enemies: list) -> str:
        if not enemies:
            return ""
        if getattr(pet, "role", "dps") == "healer":
            # 治疗宠:优先血量最低的友方(由调用方传入 allies 时)
            lowest = min(enemies, key=lambda e: e.get("hp", 0))
            return lowest.get("id", "")
        def threat(e: dict) -> float:
            # 威胁值高优先,残血优先
            return e.get("threat", 0) * 10.0 - e.get("hp", 0)
        best = max(enemies, key=threat)
        return best.get("id", "")

    # ---- bug4: 公共冷却 GCD ----
    def get_gcd(self) -> float:
        return GCD

    def can_cast(self, skill: PetSkill, current_time: float) -> bool:
        return (current_time - self.last_gcd_time >= GCD
                and skill.ready_time <= current_time)

    def cast_skill(self, pet: BattlePet, skill: PetSkill, current_time: float) -> bool:
        if not self.can_cast(skill, current_time):
            return False
        if skill.energy_cost > pet.energy:
            return False
        pet.energy -= skill.energy_cost
        skill.ready_time = current_time + max(skill.cooldown, 0)
        self.last_gcd_time = current_time
        return True

    # ---- bug5: 新宠物入场血量按比例继承并逐次递减 ----
    def get_new_pet_hp(self, pet: BattlePet) -> float:
        ratio = NEW_PET_HP_RATIO - self.switch_count * ENTRY_HP_PENALTY
        ratio = max(ratio, 0.1)
        return pet.hp * ratio

    # ---- bug6: 能量/怒气限制:普攻积攒,大招耗满能量 ----
    def get_energy_regen(self, pet: BattlePet) -> int:
        return min(pet.energy + ENERGY_REGEN_PER_TURN, MAX_ENERGY)

    def can_cast_ult(self, pet: BattlePet, skill: PetSkill) -> bool:
        return pet.energy >= ULT_ENERGY_COST and skill.energy_cost >= ULT_ENERGY_COST

    # ---- bug7: 被动叠加:同名相加,取最高由调用方按需选择 ----
    def get_passive_stacking(self, pets: list[BattlePet]) -> dict:
        stacked: dict = {}
        for pet in pets:
            for key, value in (pet.passive or {}).items():
                if isinstance(value, (int, float)):
                    stacked[key] = stacked.get(key, 0) + value
                else:
                    stacked.setdefault(key, value)
        return stacked

    def get_passive_max(self, pets: list[BattlePet]) -> dict:
        """取最高机制:同名被动取最大值"""
        result: dict = {}
        for pet in pets:
            for key, value in (pet.passive or {}).items():
                if key not in result or value > result[key]:
                    result[key] = value
        return result
