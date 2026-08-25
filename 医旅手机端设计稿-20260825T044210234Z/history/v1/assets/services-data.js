/* SECTION: services-data */
/* 医旅手机端设计稿 — 页面示例数据（图片来源：图片搜索结果，仅用于设计稿演示） */
(function () {
  'use strict';

  window.SERVICES_DATA = {
    heroImage:
      'https://agent.qianwen.com/service/0e592e92-0db1-42/a2c52caca8c971686daa9b6ef82222dd',
    categories: [
      { id: 'all', label: '全部' },
      { id: 'ortho', label: '骨科' },
      { id: 'dental', label: '牙科' },
      { id: 'wellness', label: '健康管理' }
    ],
    services: [
      {
        id: '1',
        name: '膝关节置换手术',
        hospital: '北京协和医院',
        hospitalLevel: '三级甲等',
        price: 15000,
        currency: 'EUR',
        durationDays: 21,
        category: 'ortho',
        categoryLabel: '骨科',
        image:
          'https://agent.qianwen.com/service/8592df0f-6d1b-42/995b8d4bd28907d633b884c738865ca4',
        intro:
          '由三甲医院骨科专家团队主刀，采用进口人工关节假体，帮助患者摆脱关节疼痛、恢复行走能力。',
        highlights: [
          '三甲医院骨科专家团队主刀，年手术量超千例',
          '进口人工关节假体，预期使用寿命 15-20 年',
          '费用包含术前评估、手术、住院及康复指导',
          '专属医疗顾问全程陪同，提供翻译与行程协助'
        ],
        process: [
          { step: '预约咨询', desc: '提交病历资料，医疗顾问 24 小时内响应' },
          { step: '远程评估', desc: '专家团队视频问诊，确认手术方案与报价' },
          { step: '赴华治疗', desc: '接机安排入住，完成手术与住院康复' },
          { step: '术后随访', desc: '回国后 12 个月远程随访，指导康复训练' }
        ]
      },
      {
        id: '2',
        name: '微创种植牙',
        hospital: '北京大学口腔医院',
        hospitalLevel: '三级甲等',
        price: 2500,
        currency: 'EUR',
        durationDays: 7,
        category: 'dental',
        categoryLabel: '牙科',
        image:
          'https://agent.qianwen.com/service/da0776c0-90bf-40/43e2bbd5e2902157a3c287e6dff02659',
        intro:
          '数字化导板种植技术，微创精准，采用进口种植体，让缺牙患者重获自然咀嚼与美观笑容。',
        highlights: [
          '数字化导板种植，微创精准，恢复快',
          '进口种植体，提供 10 年质保',
          '费用含全景片检查、方案设计与种植体',
          '独立诊室，全程无痛管理'
        ],
        process: [
          { step: '预约咨询', desc: '提交口腔情况，医疗顾问 24 小时内响应' },
          { step: '远程评估', desc: '医生视频看诊，确认种植方案与费用' },
          { step: '赴华治疗', desc: '到院检查、植入种植体并完成牙冠修复' },
          { step: '术后随访', desc: '定期远程回访，指导口腔维护' }
        ]
      }
    ]
  };
})();
