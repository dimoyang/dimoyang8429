"""种子数据：医院、套餐、演示用户与核心目的地（幂等）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Destination, Hospital, MedicalPackage, User
from app.security import hash_password

DEMO_EMAIL = "demo@meditour.com"
DEMO_PASSWORD = "Demo123456"


def seed_data(db: Session) -> None:
    # 演示账号由开关控制；关闭时也不会删除数据库中已存在的账号。
    if settings.SEED_DEMO_USER and db.scalar(
        select(User).where(User.email == DEMO_EMAIL)
    ) is None:
        db.add(
            User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                full_name="Demo User",
                preferred_language="en",
            )
        )

    if db.scalar(select(Hospital.id).limit(1)) is None:
        db.add_all(
            [
                Hospital(
                    name="北京协和医院",
                    name_en="Peking Union Medical College Hospital",
                    level="三级甲等",
                ),
                Hospital(
                    name="北京大学口腔医院",
                    name_en="Peking University School of Stomatology",
                    level="三级甲等",
                ),
            ]
        )

    db.flush()

    if db.scalar(select(MedicalPackage.id).limit(1)) is None:
        hospitals = {
            hospital.name_en: hospital
            for hospital in db.scalars(select(Hospital)).all()
        }
        db.add_all(
            [
                MedicalPackage(
                    name="膝关节置换手术",
                    name_en="Knee Replacement Surgery",
                    price=15000,
                    currency=settings.DEFAULT_CURRENCY,
                    duration_days=21,
                    image_url=(
                        "https://agent.qianwen.com/service/"
                        "8592df0f-6d1b-42/995b8d4bd28907d633b884c738865ca4"
                    ),
                    description=(
                        "由三甲医院骨科专家团队主刀，采用进口人工关节假体，"
                        "帮助患者摆脱关节疼痛、恢复行走能力。"
                    ),
                    description_en=(
                        "Performed by senior orthopedic specialists at a top-tier "
                        "hospital with imported joint prostheses, helping patients "
                        "relieve pain and regain mobility."
                    ),
                    category="orthopedics",
                    hospital_id=hospitals["Peking Union Medical College Hospital"].id,
                ),
                MedicalPackage(
                    name="微创种植牙",
                    name_en="Dental Implants",
                    price=2500,
                    currency=settings.DEFAULT_CURRENCY,
                    duration_days=7,
                    image_url=(
                        "https://agent.qianwen.com/service/"
                        "da0776c0-90bf-40/43e2bbd5e2902157a3c287e6dff02659"
                    ),
                    description=(
                        "数字化导板种植技术，微创精准，采用进口种植体，"
                        "让缺牙患者重获自然咀嚼与美观笑容。"
                    ),
                    description_en=(
                        "Digitally guided implant surgery with imported implants, "
                        "minimally invasive and precise, restoring natural chewing "
                        "and an aesthetic smile."
                    ),
                    category="dentistry",
                    hospital_id=hospitals["Peking University School of Stomatology"].id,
                ),
            ]
        )

    db.commit()

    _seed_destinations(db)


def _seed_destinations(db: Session) -> None:
    """核心目的地：slug 与前端本地数据保持一致。"""
    if db.scalar(select(Destination.id).limit(1)) is not None:
        return

    db.add_all(
        [
            Destination(
                id="beijing",
                name="北京",
                name_en="Beijing",
                tagline="千年古都，历史与现代交汇",
                image_url=(
                    "https://agent.qianwen.com/service/"
                    "37320046-bedd-4e/afbbffb6bdf6194f584bb626f1495045"
                ),
                search_terms=["北京", "Beijing", "长城", "Great Wall", "故宫"],
                best_season="4-5月 / 9-10月",
                suggest_days="4-6 天",
                intro=(
                    "北京是中国的首都，拥有七处世界文化遗产。"
                    "从故宫、长城到胡同四合院，三千年的历史层层展开。"
                ),
                experiences=[
                    {
                        "icon": "🏯",
                        "title": "故宫漫步",
                        "description": "世界最大的宫殿建筑群，清晨入内光线最佳",
                    },
                    {
                        "icon": "🧗",
                        "title": "长城日出",
                        "description": "慕田峪长城人少景美，可乘缆车往返",
                    },
                    {
                        "icon": "🦆",
                        "title": "北京烤鸭",
                        "description": "百年老店品尝皮脆肉嫩的挂炉烤鸭",
                    },
                ],
                tips=["地铁覆盖主要景点，建议避开黄金周", "故宫需提前实名预约"],
                sort_order=1,
            ),
            Destination(
                id="shanghai",
                name="上海",
                name_en="Shanghai",
                tagline="东方巴黎，黄浦江畔的摩登风情",
                image_url=(
                    "https://agent.qianwen.com/service/"
                    "37320046-bedd-4e/6b1f8e6f7a3f4d6c"
                ),
                search_terms=["上海", "Shanghai", "外滩", "Bund", "豫园"],
                best_season="3-5月 / 9-11月",
                suggest_days="3-4 天",
                intro=(
                    "上海是中国最国际化的城市，外滩的万国建筑与陆家嘴的"
                    "天际线隔江相望，石库门里弄藏着市井烟火。"
                ),
                experiences=[
                    {
                        "icon": "🌃",
                        "title": "外滩夜景",
                        "description": "傍晚沿江漫步，看两岸灯光依次亮起",
                    },
                    {
                        "icon": "🏮",
                        "title": "豫园老城厢",
                        "description": "江南园林与城隍庙小吃一条街",
                    },
                ],
                tips=["地铁几乎覆盖全部景点", "周末外滩人流密集，建议错峰"],
                sort_order=2,
            ),
            Destination(
                id="xian",
                name="西安",
                name_en="Xi'an",
                tagline="一眼千年，梦回大唐长安",
                image_url=(
                    "https://agent.qianwen.com/service/"
                    "37320046-bedd-4e/2c5f9a8e1b6d4f7a"
                ),
                search_terms=["西安", "Xi'an", "兵马俑", "Terracotta", "城墙"],
                best_season="3-5月 / 9-11月",
                suggest_days="3-5 天",
                intro=(
                    "西安是十三朝古都，兵马俑、古城墙与大雁塔见证着"
                    "丝绸之路起点的辉煌，回民街则延续着烟火气。"
                ),
                experiences=[
                    {
                        "icon": "🗿",
                        "title": "兵马俑",
                        "description": "世界第八大奇迹，建议请讲解员",
                    },
                    {
                        "icon": "🚲",
                        "title": "城墙骑行",
                        "description": "在完整古城墙上骑行一圈，俯瞰老城",
                    },
                ],
                tips=["兵马俑距市区较远，预留半天", "回民街注意清真饮食禁忌"],
                sort_order=3,
            ),
            Destination(
                id="chengdu",
                name="成都",
                name_en="Chengdu",
                tagline="天府之国，把节奏慢下来",
                image_url=(
                    "https://agent.qianwen.com/service/"
                    "37320046-bedd-4e/9d4e2b7c5a8f1e3d"
                ),
                search_terms=["成都", "Chengdu", "熊猫", "Panda", "火锅"],
                best_season="3-6月 / 9-11月",
                suggest_days="3-5 天",
                intro=(
                    "成都以悠闲著称，茶馆、火锅与大熊猫构成城市日常，"
                    "周边还有都江堰、青城山等世界遗产。"
                ),
                experiences=[
                    {
                        "icon": "🐼",
                        "title": "大熊猫基地",
                        "description": "清晨看熊猫进食最活跃，建议开园即到",
                    },
                    {
                        "icon": "🌶️",
                        "title": "火锅之夜",
                        "description": "本地老火锅配香油碟，微辣起步",
                    },
                ],
                tips=["熊猫基地建议早上 8 点前入园", "成都多雨，随身带伞"],
                sort_order=4,
            ),
        ]
    )
    db.commit()
