import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/data/models/hospital.dart';
import 'package:meditour_app/data/models/medical_service.dart';

/// 医疗服务仓库
///
/// 远程优先：从后端 /api/v1/medical 拉取套餐与医院并映射；
/// 后端不可达时回退到内置示例数据，保证离线可演示。
class ServiceRepository {
  ServiceRepository._();

  /// 内置示例服务数据（离线回退源，内容来源：设计稿定稿的示例数据）
  static final List<MedicalService> sampleServices = [
    MedicalService(
      id: '1',
      nameEn: 'Knee Replacement Surgery',
      nameDe: 'Kniegelenkersatzoperation',
      nameFr: 'Chirurgie de remplacement du genou',
      nameZh: '膝关节置换手术',
      hospital: '北京协和医院',
      hospitalLevel: '三级甲等',
      basePrice: 15000,
      currency: 'EUR',
      category: 'orthopedics',
      categoryLabel: '骨科',
      durationDays: 21,
      imageUrl:
          'https://agent.qianwen.com/service/8592df0f-6d1b-42/995b8d4bd28907d633b884c738865ca4',
      intro: '由三甲医院骨科专家团队主刀，采用进口人工关节假体，帮助患者摆脱关节疼痛、恢复行走能力。',
      highlights: const [
        '三甲医院骨科专家团队主刀，年手术量超千例',
        '进口人工关节假体，预期使用寿命 15-20 年',
        '费用包含术前评估、手术、住院及康复指导',
        '专属医疗顾问全程陪同，提供翻译与行程协助',
      ],
      process: const [
        ProcessStep(step: '预约咨询', description: '提交病历资料，医疗顾问 24 小时内响应'),
        ProcessStep(step: '远程评估', description: '专家团队视频问诊，确认手术方案与报价'),
        ProcessStep(step: '赴华治疗', description: '接机安排入住，完成手术与住院康复'),
        ProcessStep(step: '术后随访', description: '回国后 12 个月远程随访，指导康复训练'),
      ],
    ),
    MedicalService(
      id: '2',
      nameEn: 'Dental Implants',
      nameDe: 'Zahnimplantate',
      nameFr: 'Implants dentaires',
      nameZh: '微创种植牙',
      hospital: '北京大学口腔医院',
      hospitalLevel: '三级甲等',
      basePrice: 2500,
      currency: 'EUR',
      category: 'dentistry',
      categoryLabel: '牙科',
      durationDays: 7,
      imageUrl:
          'https://agent.qianwen.com/service/da0776c0-90bf-40/43e2bbd5e2902157a3c287e6dff02659',
      intro: '数字化导板种植技术，微创精准，采用进口种植体，让缺牙患者重获自然咀嚼与美观笑容。',
      highlights: const [
        '数字化导板种植，微创精准，恢复快',
        '进口种植体，提供 10 年质保',
        '费用含全景片检查、方案设计与种植体',
        '独立诊室，全程无痛管理',
      ],
      process: const [
        ProcessStep(step: '预约咨询', description: '提交口腔情况，医疗顾问 24 小时内响应'),
        ProcessStep(step: '远程评估', description: '医生视频看诊，确认种植方案与费用'),
        ProcessStep(step: '赴华治疗', description: '到院检查、植入种植体并完成牙冠修复'),
        ProcessStep(step: '术后随访', description: '定期远程回访，指导口腔维护'),
      ],
    ),
  ];

  static List<MedicalService> _cache = [];
  static bool _lastLoadWasSample = false;

  /// 最近一次加载是否回退到了示例数据（用于页面展示离线提示）。
  static bool get lastLoadWasSample => _lastLoadWasSample;

  /// 获取全部医疗服务：远程优先，失败回退示例数据。
  static Future<List<MedicalService>> getServices({
    bool forceRemote = false,
  }) async {
    if (_cache.isNotEmpty && !forceRemote) {
      return List.unmodifiable(_cache);
    }
    try {
      final results = await Future.wait([
        ApiService.instance.getPackages(pageSize: 100),
        ApiService.instance.getHospitals(),
      ]);
      final packages = results[0];
      final hospitals = results[1]
          .map(HospitalInfo.fromJson)
          .toList(growable: false);
      final hospitalById = {for (final h in hospitals) h.id: h};

      _cache = packages.map((pkg) {
        final hospital = hospitalById[pkg['hospital_id']];
        return MedicalService.fromPackage(
          pkg,
          hospitalName: hospital?.name ?? '',
          hospitalLevel: hospital?.level ?? '',
        );
      }).toList();
      _lastLoadWasSample = false;
    } catch (_) {
      _cache = sampleServices;
      _lastLoadWasSample = true;
    }
    return List.unmodifiable(_cache);
  }

  /// 按 id 获取单个服务；缓存为空时先加载（深链直达场景）。
  static Future<MedicalService?> getService(String id) async {
    if (_cache.isEmpty) {
      await getServices();
    }
    return findById(id);
  }

  /// 根据 id 查找服务（同步，仅查已加载缓存）
  static MedicalService? findById(String id) {
    for (final service in _cache) {
      if (service.id == id) {
        return service;
      }
    }
    return null;
  }
}
