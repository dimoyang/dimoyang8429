"""种子数据：医院、套餐、演示用户与核心目的地（幂等）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ContentTranslation,
    Destination,
    Hospital,
    MedicalPackage,
    User,
)
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

    _seed_translations(db)
    _seed_destinations(db)
    if settings.SEED_DEMO_DATA:
        # 联调演示数据：默认关闭，只在显式开启时做增量插入。
        _seed_demo_catalog(db)


def _seed_translations(db: Session) -> None:
    """德语示例译文，仅用于验证多语言接口与回退逻辑。

    这是演示数据，不是可直接上线的人工译文；生产内容必须由人工翻译并复核。
    """
    package = db.scalar(
        select(MedicalPackage).where(
            MedicalPackage.name_en == "Knee Replacement Surgery"
        )
    )
    hospital = db.scalar(
        select(Hospital).where(
            Hospital.name_en == "Peking Union Medical College Hospital"
        )
    )

    entries: list[tuple[str, int, str, str, str]] = []
    if package is not None:
        entries.extend(
            [
                (
                    "package",
                    package.id,
                    "de",
                    "name",
                    "Kniegelenkersatz (Knie-TEP)",
                ),
                (
                    "package",
                    package.id,
                    "de",
                    "description",
                    "Durchgeführt von einem erfahrenen orthopädischen Team "
                    "einer Top-Klinik mit importierten Gelenkimplantaten: "
                    "weniger Schmerzen und mehr Mobilität.",
                ),
            ]
        )
    if hospital is not None:
        entries.append(
            (
                "hospital",
                hospital.id,
                "de",
                "name",
                "Peking-Union-Krankenhaus",
            )
        )

    for entity_type, entity_id, lang, field, value in entries:
        # content_translations.entity_id 统一为字符串，兼容整数主键与 slug。
        entity_id = str(entity_id)
        exists = db.scalar(
            select(ContentTranslation.id).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.entity_id == entity_id,
                ContentTranslation.lang == lang,
                ContentTranslation.field == field,
            )
        )
        if exists is None:
            db.add(
                ContentTranslation(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    lang=lang,
                    field=field,
                    value=value,
                )
            )
    db.commit()


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


# ---------------------------------------------------------------------------
# 联调演示数据（MEDITOUR_SEED_DEMO_DATA=true 时才写入）
#
# 只做增量插入：以 name_en / 目的地 id 判定是否存在，重复启动不会重复写入，
# 也不会修改或删除已有数据。默认关闭，生产环境不要开启。
# ---------------------------------------------------------------------------

DEMO_HOSPITALS = [
    {
        "name": "复旦大学附属肿瘤医院",
        "name_en": "Fudan University Shanghai Cancer Center",
        "level": "三级甲等",
    },
    {
        "name": "四川大学华西医院",
        "name_en": "West China Hospital",
        "level": "三级甲等",
    },
    {
        "name": "首都医科大学附属北京同仁医院",
        "name_en": "Beijing Tongren Hospital",
        "level": "三级甲等",
    },
    {
        "name": "上海交通大学医学院附属第九人民医院",
        "name_en": "Shanghai Ninth People's Hospital",
        "level": "三级甲等",
    },
    {
        "name": "广东省人民医院",
        "name_en": "Guangdong Provincial People's Hospital",
        "level": "三级甲等",
    },
    {
        "name": "浙江大学医学院附属第一医院",
        "name_en": "Zhejiang University School of Medicine First Affiliated Hospital",
        "level": "三级甲等",
    },
]

# 20 个套餐，覆盖 12 个分类、300–45000 价格区间与 3–30 天疗程。
DEMO_PACKAGES = [
    {
        "name": "全髋关节置换手术",
        "name_en": "Total Hip Replacement",
        "price": 18000,
        "duration_days": 18,
        "category": "orthopedics",
        "hospital_name_en": "West China Hospital",
        "description": "采用进口髋关节假体，术后配合专业康复训练，帮助恢复行走能力。",
        "description_en": "Imported hip prosthesis with a structured rehabilitation program to restore walking ability.",
    },
    {
        "name": "脊柱融合手术",
        "name_en": "Spinal Fusion Surgery",
        "price": 22000,
        "duration_days": 21,
        "category": "orthopedics",
        "hospital_name_en": "Peking Union Medical College Hospital",
        "description": "针对腰椎间盘突出与椎体滑脱的微创融合方案，减少周围组织损伤。",
        "description_en": "Minimally invasive fusion for disc herniation and spondylolisthesis with less tissue damage.",
    },
    {
        "name": "All-on-4 全口种植",
        "name_en": "All-on-4 Dental Implants",
        "price": 8000,
        "duration_days": 10,
        "category": "dentistry",
        "hospital_name_en": "Shanghai Ninth People's Hospital",
        "description": "四颗种植体支撑整排固定假牙，适合多颗牙缺失患者。",
        "description_en": "Four implants support a full fixed arch, suitable for patients with multiple missing teeth.",
    },
    {
        "name": "隐形正畸",
        "name_en": "Clear Aligner Orthodontics",
        "price": 3600,
        "duration_days": 30,
        "category": "dentistry",
        "hospital_name_en": "Peking University School of Stomatology",
        "description": "数字化取模与隐形牙套方案，复诊周期灵活。",
        "description_en": "Digital scanning with clear aligners and a flexible follow-up schedule.",
    },
    {
        "name": "冷光美白",
        "name_en": "Teeth Whitening",
        "price": 300,
        "duration_days": 3,
        "category": "dentistry",
        "hospital_name_en": "Shanghai Ninth People's Hospital",
        "description": "诊室冷光美白，单次可见色阶提升，适合轻度色素沉着。",
        "description_en": "In-office whitening with visible shade improvement for mild staining.",
    },
    {
        "name": "冠状动脉搭桥手术",
        "name_en": "Coronary Artery Bypass Graft",
        "price": 32000,
        "duration_days": 25,
        "category": "cardiology",
        "hospital_name_en": "Guangdong Provincial People's Hospital",
        "description": "心外科团队完成搭桥手术，术后进入心脏监护与康复流程。",
        "description_en": "Bypass surgery by a cardiac surgical team, followed by monitored recovery.",
    },
    {
        "name": "心脏瓣膜置换",
        "name_en": "Cardiac Valve Replacement",
        "price": 38000,
        "duration_days": 28,
        "category": "cardiology",
        "hospital_name_en": "West China Hospital",
        "description": "提供机械瓣与生物瓣两种方案，术前由多学科团队评估。",
        "description_en": "Mechanical or biological valve options with multidisciplinary pre-operative assessment.",
    },
    {
        "name": "全身肿瘤筛查",
        "name_en": "Comprehensive Cancer Screening",
        "price": 1200,
        "duration_days": 4,
        "category": "oncology",
        "hospital_name_en": "Fudan University Shanghai Cancer Center",
        "description": "结合影像、肿瘤标志物与专科问诊的全身早筛方案。",
        "description_en": "Whole-body early screening combining imaging, tumor markers and specialist consultation.",
    },
    {
        "name": "质子治疗评估",
        "name_en": "Proton Therapy Assessment",
        "price": 45000,
        "duration_days": 30,
        "category": "oncology",
        "hospital_name_en": "Fudan University Shanghai Cancer Center",
        "description": "面向实体瘤患者的质子治疗适应症评估与定位准备。",
        "description_en": "Proton therapy eligibility assessment and planning preparation for solid tumors.",
    },
    {
        "name": "SMILE 全飞秒激光",
        "name_en": "SMILE Laser Eye Surgery",
        "price": 1600,
        "duration_days": 5,
        "category": "ophthalmology",
        "hospital_name_en": "Beijing Tongren Hospital",
        "description": "无瓣微创近视矫正，术后干眼风险较低，恢复快。",
        "description_en": "Flap-free minimally invasive myopia correction with fast recovery.",
    },
    {
        "name": "白内障超声乳化手术",
        "name_en": "Cataract Surgery",
        "price": 900,
        "duration_days": 7,
        "category": "ophthalmology",
        "hospital_name_en": "Beijing Tongren Hospital",
        "description": "超声乳化联合人工晶体植入，可选择多焦点晶体。",
        "description_en": "Phacoemulsification with intraocular lens implantation, including multifocal options.",
    },
    {
        "name": "全面体检套餐",
        "name_en": "Full-Body Health Checkup",
        "price": 800,
        "duration_days": 3,
        "category": "wellness",
        "hospital_name_en": "Zhejiang University School of Medicine First Affiliated Hospital",
        "description": "涵盖血检、影像与专科评估的一站式体检，出具中英文报告。",
        "description_en": "One-stop checkup with labs, imaging and specialist review, report in Chinese and English.",
    },
    {
        "name": "中医康养疗程",
        "name_en": "Traditional Chinese Medicine Retreat",
        "price": 2400,
        "duration_days": 14,
        "category": "wellness",
        "hospital_name_en": "Zhejiang University School of Medicine First Affiliated Hospital",
        "description": "针灸、推拿与中药调理结合的两周康养计划。",
        "description_en": "Two-week wellness plan combining acupuncture, massage and herbal medicine.",
    },
    {
        "name": "试管婴儿周期套餐",
        "name_en": "IVF Cycle Package",
        "price": 9500,
        "duration_days": 21,
        "category": "fertility",
        "hospital_name_en": "Shanghai Ninth People's Hospital",
        "description": "包含促排、取卵、胚胎培养与移植的一个完整 IVF 周期。",
        "description_en": "One complete IVF cycle covering stimulation, retrieval, culture and transfer.",
    },
    {
        "name": "鼻综合整形",
        "name_en": "Rhinoplasty",
        "price": 3200,
        "duration_days": 10,
        "category": "plastic",
        "hospital_name_en": "Shanghai Ninth People's Hospital",
        "description": "根据面部比例设计鼻部形态，术后提供随访与消肿管理。",
        "description_en": "Nose reshaping designed around facial proportions with follow-up care.",
    },
    {
        "name": "植发手术",
        "name_en": "Hair Transplant",
        "price": 2800,
        "duration_days": 12,
        "category": "plastic",
        "hospital_name_en": "Shanghai Ninth People's Hospital",
        "description": "FUE 无痕植发，按毛囊单位计价，术前进行供区评估。",
        "description_en": "Scarless FUE transplant priced per graft, with donor-area assessment.",
    },
    {
        "name": "卒中康复疗程",
        "name_en": "Stroke Rehabilitation Program",
        "price": 12500,
        "duration_days": 30,
        "category": "neurology",
        "hospital_name_en": "Guangdong Provincial People's Hospital",
        "description": "物理治疗、作业治疗与言语训练组成的四周康复计划。",
        "description_en": "Four-week rehabilitation combining physiotherapy, occupational and speech therapy.",
    },
    {
        "name": "胃肠镜检查",
        "name_en": "Gastroscopy and Colonoscopy",
        "price": 650,
        "duration_days": 3,
        "category": "gastroenterology",
        "hospital_name_en": "West China Hospital",
        "description": "无痛胃肠镜联合检查，发现息肉可当场处理。",
        "description_en": "Painless combined gastroscopy and colonoscopy with same-session polyp removal.",
    },
    {
        "name": "银屑病治疗疗程",
        "name_en": "Psoriasis Treatment Program",
        "price": 2100,
        "duration_days": 14,
        "category": "dermatology",
        "hospital_name_en": "Zhejiang University School of Medicine First Affiliated Hospital",
        "description": "光疗与系统用药联合方案，两周内评估皮损改善情况。",
        "description_en": "Phototherapy combined with systemic medication, reviewed over two weeks.",
    },
    {
        "name": "儿童心脏评估",
        "name_en": "Pediatric Cardiac Assessment",
        "price": 1500,
        "duration_days": 6,
        "category": "pediatrics",
        "hospital_name_en": "Guangdong Provincial People's Hospital",
        "description": "儿童心脏超声、心电图与专科问诊，提供中英文报告。",
        "description_en": "Pediatric echocardiography, ECG and specialist consultation with bilingual report.",
    },
]

# 演示译文：套餐与医院各取一部分，覆盖 de / fr 两种语言。
# 生产内容必须由人工翻译并复核，这里只用于联调多语言与回退逻辑。
DEMO_TRANSLATIONS = [
    ("package", "Total Hip Replacement", "de", "name", "Totalendoprothese der Hüfte"),
    (
        "package",
        "Total Hip Replacement",
        "de",
        "description",
        "Importierte Hüftprothese mit strukturierter Rehabilitation für mehr Mobilität.",
    ),
    ("package", "Total Hip Replacement", "fr", "name", "Prothèse totale de hanche"),
    (
        "package",
        "Total Hip Replacement",
        "fr",
        "description",
        "Prothèse de hanche importée avec un programme de rééducation structuré.",
    ),
    ("package", "All-on-4 Dental Implants", "de", "name", "All-on-4 Zahnimplantate"),
    (
        "package",
        "All-on-4 Dental Implants",
        "de",
        "description",
        "Vier Implantate tragen einen festen Zahnbogen bei mehreren fehlenden Zähnen.",
    ),
    ("package", "All-on-4 Dental Implants", "fr", "name", "Implants dentaires All-on-4"),
    (
        "package",
        "All-on-4 Dental Implants",
        "fr",
        "description",
        "Quatre implants soutiennent une arcade fixe en cas de dents manquantes.",
    ),
    (
        "package",
        "Coronary Artery Bypass Graft",
        "de",
        "name",
        "Koronare Bypass-Operation",
    ),
    (
        "package",
        "Coronary Artery Bypass Graft",
        "de",
        "description",
        "Bypass-Operation durch ein herzchirurgisches Team mit überwachter Erholung.",
    ),
    (
        "package",
        "Coronary Artery Bypass Graft",
        "fr",
        "name",
        "Pontage coronarien",
    ),
    (
        "package",
        "Coronary Artery Bypass Graft",
        "fr",
        "description",
        "Pontage réalisé par une équipe chirurgicale cardiaque avec suivi post-opératoire.",
    ),
    (
        "package",
        "Comprehensive Cancer Screening",
        "de",
        "name",
        "Umfassende Krebsvorsorge",
    ),
    (
        "package",
        "Comprehensive Cancer Screening",
        "de",
        "description",
        "Ganzkörper-Früherkennung mit Bildgebung und Tumormarkern.",
    ),
    (
        "package",
        "Comprehensive Cancer Screening",
        "fr",
        "name",
        "Dépistage complet du cancer",
    ),
    (
        "package",
        "Comprehensive Cancer Screening",
        "fr",
        "description",
        "Dépistage précoce complet associant imagerie et marqueurs tumoraux.",
    ),
    ("package", "SMILE Laser Eye Surgery", "de", "name", "SMILE-Laseroperation"),
    (
        "package",
        "SMILE Laser Eye Surgery",
        "de",
        "description",
        "Minimalinvasive Myopiekorrektur ohne Flap mit schneller Erholung.",
    ),
    ("package", "SMILE Laser Eye Surgery", "fr", "name", "Chirurgie laser SMILE"),
    (
        "package",
        "SMILE Laser Eye Surgery",
        "fr",
        "description",
        "Correction de la myopie sans volet, peu invasive et à récupération rapide.",
    ),
    ("package", "IVF Cycle Package", "de", "name", "IVF-Zykluspaket"),
    (
        "package",
        "IVF Cycle Package",
        "de",
        "description",
        "Ein vollständiger IVF-Zyklus mit Stimulation, Punktion, Kultur und Transfer.",
    ),
    ("package", "IVF Cycle Package", "fr", "name", "Forfait cycle FIV"),
    (
        "package",
        "IVF Cycle Package",
        "fr",
        "description",
        "Un cycle FIV complet : stimulation, ponction, culture et transfert.",
    ),
    ("package", "Rhinoplasty", "de", "name", "Nasenkorrektur"),
    (
        "package",
        "Rhinoplasty",
        "de",
        "description",
        "Individuelle Nasenformung mit Nachsorge und Abschwellmanagement.",
    ),
    ("package", "Rhinoplasty", "fr", "name", "Rhinoplastie"),
    (
        "package",
        "Rhinoplasty",
        "fr",
        "description",
        "Remodelage nasal personnalisé avec suivi et gestion de l'œdème.",
    ),
    (
        "package",
        "Stroke Rehabilitation Program",
        "de",
        "name",
        "Schlaganfall-Rehabilitation",
    ),
    (
        "package",
        "Stroke Rehabilitation Program",
        "de",
        "description",
        "Vierwöchige Rehabilitation aus Physio-, Ergo- und Sprachtherapie.",
    ),
    (
        "package",
        "Stroke Rehabilitation Program",
        "fr",
        "name",
        "Programme de rééducation après AVC",
    ),
    (
        "package",
        "Stroke Rehabilitation Program",
        "fr",
        "description",
        "Quatre semaines de kinésithérapie, ergothérapie et orthophonie.",
    ),
    ("hospital", "West China Hospital", "de", "name", "Westchina-Krankenhaus"),
    ("hospital", "West China Hospital", "fr", "name", "Hôpital West China"),
    (
        "hospital",
        "Fudan University Shanghai Cancer Center",
        "de",
        "name",
        "Krebszentrum der Fudan-Universität Shanghai",
    ),
    (
        "hospital",
        "Fudan University Shanghai Cancer Center",
        "fr",
        "name",
        "Centre anticancéreux de l'Université Fudan de Shanghai",
    ),
    (
        "hospital",
        "Shanghai Ninth People's Hospital",
        "de",
        "name",
        "Neuntes Volkskrankenhaus Shanghai",
    ),
    (
        "hospital",
        "Shanghai Ninth People's Hospital",
        "fr",
        "name",
        "Neuvième hôpital populaire de Shanghai",
    ),
    (
        "hospital",
        "Zhejiang University School of Medicine First Affiliated Hospital",
        "de",
        "name",
        "Erste angegliederte Klinik der Zhejiang-Universität",
    ),
    (
        "hospital",
        "Zhejiang University School of Medicine First Affiliated Hospital",
        "fr",
        "name",
        "Premier hôpital affilié de l'Université du Zhejiang",
    ),
]

# 10 个目的地：与现有 4 个合计 14 个，足够验证一页以上的列表与搜索。
DEMO_DESTINATIONS = [
    {
        "id": "guangzhou",
        "name": "广州",
        "name_en": "Guangzhou",
        "tagline": "花城早茶，珠江夜色",
        "image_url": "https://picsum.photos/seed/guangzhou/800/600",
        "search_terms": ["广州", "Guangzhou", "早茶", "珠江", "陈家祠"],
        "best_season": "10-12月",
        "suggest_days": "2-4 天",
        "intro": "广州既有骑楼老街与早茶文化，也有珠江新城的现代天际线。",
        "experiences": [
            {"icon": "🥟", "title": "广式早茶", "description": "一盅两件，从清晨吃到中午"},
            {"icon": "🌉", "title": "珠江夜游", "description": "乘船看两岸灯光与广州塔"},
        ],
        "tips": ["夏季湿热，注意补水", "早茶高峰需提前取号"],
        "sort_order": 5,
    },
    {
        "id": "shenzhen",
        "name": "深圳",
        "name_en": "Shenzhen",
        "tagline": "山海之间的年轻城市",
        "image_url": "https://picsum.photos/seed/shenzhen/800/600",
        "search_terms": ["深圳", "Shenzhen", "大梅沙", "华侨城", "科技园"],
        "best_season": "10-12月",
        "suggest_days": "2-3 天",
        "intro": "深圳从渔村发展为创新之城，海岸线、主题公园与城市绿地都很容易到达。",
        "experiences": [
            {"icon": "🏖️", "title": "大梅沙海滨", "description": "城市边缘的沙滩与栈道"},
            {"icon": "🎢", "title": "主题公园", "description": "适合家庭同行的全天行程"},
        ],
        "tips": ["地铁覆盖广，跨区通勤时间长", "海边紫外线强，注意防晒"],
        "sort_order": 6,
    },
    {
        "id": "hangzhou",
        "name": "杭州",
        "name_en": "Hangzhou",
        "tagline": "上有天堂，下有苏杭",
        "image_url": "https://picsum.photos/seed/hangzhou/800/600",
        "search_terms": ["杭州", "Hangzhou", "西湖", "龙井", "灵隐寺"],
        "best_season": "3-5月 / 9-11月",
        "suggest_days": "2-4 天",
        "intro": "西湖十景与龙井茶园构成了杭州最经典的慢旅行路线。",
        "experiences": [
            {"icon": "🌊", "title": "西湖环湖", "description": "骑行或步行，清晨人最少"},
            {"icon": "🍵", "title": "龙井问茶", "description": "茶园品茶并了解炒茶工艺"},
        ],
        "tips": ["节假日西湖周边限行", "梅雨季随身带伞"],
        "sort_order": 7,
    },
    {
        "id": "suzhou",
        "name": "苏州",
        "name_en": "Suzhou",
        "tagline": "园林与水巷里的江南",
        "image_url": "https://picsum.photos/seed/suzhou/800/600",
        "search_terms": ["苏州", "Suzhou", "拙政园", "平江路", "昆曲"],
        "best_season": "3-5月 / 9-11月",
        "suggest_days": "2-3 天",
        "intro": "古典园林、评弹与平江路水巷，适合把行程排得松一些。",
        "experiences": [
            {"icon": "🏯", "title": "拙政园", "description": "江南园林代表，建议开园即入"},
            {"icon": "🎼", "title": "昆曲评弹", "description": "在茶馆听一段本地曲艺"},
        ],
        "tips": ["园林需提前预约", "老城区步行即可串联多个景点"],
        "sort_order": 8,
    },
    {
        "id": "nanjing",
        "name": "南京",
        "name_en": "Nanjing",
        "tagline": "六朝古都，梧桐深巷",
        "image_url": "https://picsum.photos/seed/nanjing/800/600",
        "search_terms": ["南京", "Nanjing", "中山陵", "夫子庙", "城墙"],
        "best_season": "3-5月 / 9-11月",
        "suggest_days": "2-4 天",
        "intro": "南京的历史层次密集，从明城墙到民国建筑，适合慢慢走。",
        "experiences": [
            {"icon": "🌳", "title": "梧桐大道", "description": "秋季法桐落叶最有氛围"},
            {"icon": "🏛️", "title": "中山陵", "description": "沿台阶上行，俯瞰紫金山"},
        ],
        "tips": ["夏季闷热，行程安排避开正午", "博物院需提前预约"],
        "sort_order": 9,
    },
    {
        "id": "chongqing",
        "name": "重庆",
        "name_en": "Chongqing",
        "tagline": "山城夜景，火锅江湖",
        "image_url": "https://picsum.photos/seed/chongqing/800/600",
        "search_terms": ["重庆", "Chongqing", "洪崖洞", "火锅", "长江索道"],
        "best_season": "3-5月 / 9-11月",
        "suggest_days": "2-4 天",
        "intro": "立体山城的地形本身就是景点，夜晚的江景与火锅同样难忘。",
        "experiences": [
            {"icon": "🌆", "title": "洪崖洞夜景", "description": "从对岸看吊脚楼灯光"},
            {"icon": "🌶️", "title": "老火锅", "description": "九宫格锅底，微辣也很够味"},
        ],
        "tips": ["导航按楼层定位，容易走错", "夏季高温，备好防晒与饮水"],
        "sort_order": 10,
    },
    {
        "id": "kunming",
        "name": "昆明",
        "name_en": "Kunming",
        "tagline": "四季如春，花开不败",
        "image_url": "https://picsum.photos/seed/kunming/800/600",
        "search_terms": ["昆明", "Kunming", "滇池", "石林", "鲜花"],
        "best_season": "全年",
        "suggest_days": "2-4 天",
        "intro": "昆明气候温和，是进入云南各地的中转站，也适合短途慢游。",
        "experiences": [
            {"icon": "🌸", "title": "斗南花市", "description": "亚洲大型鲜花交易市场"},
            {"icon": "🕊️", "title": "滇池海埂", "description": "冬季看红嘴鸥，夏季看湖景"},
        ],
        "tips": ["昼夜温差大，带一件外套", "高原紫外线强"],
        "sort_order": 11,
    },
    {
        "id": "lhasa",
        "name": "拉萨",
        "name_en": "Lhasa",
        "tagline": "雪域高原，信仰之城",
        "image_url": "https://picsum.photos/seed/lhasa/800/600",
        "search_terms": ["拉萨", "Lhasa", "布达拉宫", "大昭寺", "高原"],
        "best_season": "5-10月",
        "suggest_days": "4-6 天",
        "intro": "布达拉宫与大昭寺是拉萨的核心，抵达后需要给身体适应高原的时间。",
        "experiences": [
            {"icon": "🏔️", "title": "布达拉宫", "description": "需提前预约并按指定时段进入"},
            {"icon": "🛕", "title": "八廓街", "description": "清晨随转经人流走一圈"},
        ],
        "tips": ["首日避免剧烈运动", "高原反应明显时及时就医"],
        "sort_order": 12,
    },
    {
        "id": "harbin",
        "name": "哈尔滨",
        "name_en": "Harbin",
        "tagline": "冰雪之城，欧陆风情",
        "image_url": "https://picsum.photos/seed/harbin/800/600",
        "search_terms": ["哈尔滨", "Harbin", "冰雪大世界", "中央大街", "索菲亚"],
        "best_season": "12-2月",
        "suggest_days": "2-4 天",
        "intro": "冬季的冰雕与中央大街的欧式建筑是哈尔滨最鲜明的两张名片。",
        "experiences": [
            {"icon": "🧊", "title": "冰雪大世界", "description": "夜间灯光下的冰雕最壮观"},
            {"icon": "🏛️", "title": "中央大街", "description": "面包石路面与老建筑"},
        ],
        "tips": ["冬季气温可低于 -25°C，做好保暖", "冰雪季住宿需提前预订"],
        "sort_order": 13,
    },
    {
        "id": "qingdao",
        "name": "青岛",
        "name_en": "Qingdao",
        "tagline": "红瓦绿树，碧海蓝天",
        "image_url": "https://picsum.photos/seed/qingdao/800/600",
        "search_terms": ["青岛", "Qingdao", "栈桥", "八大关", "啤酒"],
        "best_season": "5-10月",
        "suggest_days": "2-4 天",
        "intro": "老城区的红瓦屋顶与海岸线相连，适合步行与骑行。",
        "experiences": [
            {"icon": "🍺", "title": "啤酒博物馆", "description": "了解酿造历史并品尝原浆"},
            {"icon": "🌊", "title": "八大关", "description": "沿海步行看各国建筑"},
        ],
        "tips": ["夏季海边人多，建议清晨前往", "海风大，早晚温差明显"],
        "sort_order": 14,
    },
]


def _seed_demo_catalog(db: Session) -> None:
    """写入联调演示目录数据；只增量插入，可安全重复执行。"""
    existing_hospitals = set(db.scalars(select(Hospital.name_en)).all())
    for item in DEMO_HOSPITALS:
        if item["name_en"] not in existing_hospitals:
            db.add(Hospital(**item))
    db.flush()

    hospital_by_name = {
        hospital.name_en: hospital for hospital in db.scalars(select(Hospital)).all()
    }
    existing_packages = set(db.scalars(select(MedicalPackage.name_en)).all())
    for item in DEMO_PACKAGES:
        if item["name_en"] in existing_packages:
            continue
        payload = dict(item)
        hospital_name = payload.pop("hospital_name_en")
        db.add(
            MedicalPackage(
                currency=settings.DEFAULT_CURRENCY,
                hospital_id=hospital_by_name[hospital_name].id,
                **payload,
            )
        )

    existing_destinations = set(db.scalars(select(Destination.id)).all())
    for item in DEMO_DESTINATIONS:
        if item["id"] not in existing_destinations:
            db.add(Destination(**item))
    db.flush()

    package_by_name = {
        package.name_en: package for package in db.scalars(select(MedicalPackage)).all()
    }
    for entity_type, name_en, lang, field, value in DEMO_TRANSLATIONS:
        lookup = package_by_name if entity_type == "package" else hospital_by_name
        entity = lookup.get(name_en)
        if entity is None:
            continue
        exists = db.scalar(
            select(ContentTranslation.id).where(
                ContentTranslation.entity_type == entity_type,
                ContentTranslation.entity_id == str(entity.id),
                ContentTranslation.lang == lang,
                ContentTranslation.field == field,
            )
        )
        if exists is None:
            db.add(
                ContentTranslation(
                    entity_type=entity_type,
                    entity_id=str(entity.id),
                    lang=lang,
                    field=field,
                    value=value,
                )
            )
    db.commit()

