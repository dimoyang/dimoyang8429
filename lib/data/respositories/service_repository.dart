import 'package:meditour_app/data/models/medical_service.dart';

/// 医疗服务仓库
///
/// 当前阶段使用内存中的示例数据；接入后端后替换为真实 API 调用。
class ServiceRepository {
  ServiceRepository._();

  /// 应用内共享的示例服务数据（内容来源：设计稿定稿的示例数据）
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

  /// 获取全部医疗服务
  static Future<List<MedicalService>> getServices() async {
    // TODO: 替换为 ApiService 的真实请求
    return List.unmodifiable(sampleServices);
  }

  /// 根据 id 查找服务
  static MedicalService? findById(String id) {
    for (final service in sampleServices) {
      if (service.id == id) {
        return service;
      }
    }
    return null;
  }
}
