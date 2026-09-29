"""宠物出战与技能循环系统 - 含7个bug"""
from dataclasses import dataclass, field

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
        self.switch_cd: float = 0  # bug1: 无切换冷却

    def switch_pet(self, pet_id: str, current_time: float) -> bool:
        # bug1: 无冷却
        self.active_pet = pet_id
        return True

    def select_skill(self, pet: BattlePet, target_hp: float, target_type: str) -> PetSkill:
        # bug2: 固定优先级
        return pet.skills[0]

    def select_target(self, pet: BattlePet, enemies: list) -> str:
        # bug3: 只看最近
        return enemies[0] if enemies else ""

    def get_gcd(self) -> float:
        # bug4: 无GCD
        return 0.0

    def get_new_pet_hp(self, pet: BattlePet) -> float:
        # bug5: 新宠物满血
        return pet.hp

    def get_energy_regen(self, pet: BattlePet) -> int:
        # bug6: 无能量限制
        return 100

    def get_passive_stacking(self, pets: list[BattlePet]) -> dict:
        # bug7: 被动不叠加
        return {}
