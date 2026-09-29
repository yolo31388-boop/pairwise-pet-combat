"""宠物出战与技能循环系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pet.battle import PetBattle, BattlePet, PetSkill

class TestSwitchCooldown:
    def test_pet_switch_has_cooldown(self):
        pb = PetBattle()
        pb.switch_cd = 10.0
        assert pb.switch_pet("p1", 5.0) == False  # bug1: True
        assert pb.switch_pet("p1", 15.0) == True

class TestSkillSelectionBySituation:
    def test_low_hp_target_gets_finisher(self):
        pb = PetBattle()
        pet = BattlePet("p1", "pet", skills=[
            PetSkill("s1", "normal", 10, priority=1),
            PetSkill("s2", "finisher", 100, priority=2),
        ])
        skill = pb.select_skill(pet, target_hp=5, target_type="normal")
        assert skill.sid == "s2"  # bug2: 固定返回s1

class TestTargetSelection:
    def test_prioritizes_low_hp_target(self):
        pb = PetBattle()
        pet = BattlePet("p1", "pet")
        enemies = [{"id": "e1", "hp": 100}, {"id": "e2", "hp": 10}]
        target = pb.select_target(pet, enemies)
        assert target == "e2"  # bug3: 返回e1

class TestGlobalCooldown:
    def test_skills_have_gcd(self):
        pb = PetBattle()
        assert pb.get_gcd() > 0  # bug4: 0

class TestNewPetNotFullHp:
    def test_switched_pet_has_reduced_hp(self):
        pb = PetBattle()
        pet = BattlePet("p1", "pet", hp=100)
        hp = pb.get_new_pet_hp(pet)
        assert hp < 100  # bug5: 满血

class TestEnergyLimitation:
    def test_skill_energy_cost_matters(self):
        pb = PetBattle()
        pet = BattlePet("p1", "pet", energy=0)
        regen = pb.get_energy_regen(pet)
        # 能量不应该每回合回满
        assert regen < 100  # bug6: 100

class TestPassiveStacking:
    def test_multiple_pet_passives_stack(self):
        pb = PetBattle()
        pets = [
            BattlePet("p1", "p1", passive={"atk": 10}),
            BattlePet("p2", "p2", passive={"atk": 20}),
        ]
        result = pb.get_passive_stacking(pets)
        assert result.get("atk", 0) > 0  # bug7: 空
