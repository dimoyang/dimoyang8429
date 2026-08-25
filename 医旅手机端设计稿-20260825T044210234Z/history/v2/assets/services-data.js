/* SECTION: app-data */
/* 医旅手机端设计稿 — 页面示例数据（图片来源：图片搜索结果，仅用于设计稿演示） */
(function () {
  'use strict';

  window.APP_DATA = {
    heroImage:
      'https://agent.qianwen.com/service/e2da4fa3-c27e-4f/832861465aa0afce641df2da4babbb2c',

    /* ---- 热门目的地 ---- */
    destinations: [
      {
        id: 'beijing',
        name: '北京',
        en: 'Beijing',
        tagline: '千年古都，历史与现代交汇',
        image:
          'https://agent.qianwen.com/service/37320046-bedd-4e/afbbffb6bdf6194f584bb626f1495045',
        bestSeason: '4-5月 / 9-10月',
        suggestDays: '4-6 天',
        intro:
          '北京是中国的首都，拥有七处世界文化遗产。从故宫、长城到胡同四合院，三千年的历史层层展开，798 艺术区与三里屯又为它注入年轻的活力。',
        experiences: [
          { icon: '🏯', title: '故宫漫步', desc: '世界最大的宫殿建筑群，清晨入内光线最佳' },
          { icon: '🧗', title: '长城日出', desc: '慕田峪长城人少景美，可乘缆车往返' },
          { icon: '🦆', title: '北京烤鸭', desc: '百年老店品尝皮脆肉嫩的挂炉烤鸭' },
          { icon: '🛖', title: '胡同游', desc: '乘人力车穿行小巷，体验老北京生活' }
        ],
        tips: [
          '故宫门票需提前 7 天在官方小程序预约',
          '首都机场乘机场快轨 30 分钟直达市区',
          '春季偶有沙尘，建议随身备口罩'
        ]
      },
      {
        id: 'shanghai',
        name: '上海',
        en: 'Shanghai',
        tagline: '东方巴黎，黄浦江畔的摩登风情',
        image:
          'https://agent.qianwen.com/service/678e78be-3b65-49/8f0b9c0d07d33d6b79c0d698b2bdaa8a',
        bestSeason: '4-5月 / 10-11月',
        suggestDays: '3-4 天',
        intro:
          '上海是一座魔幻都市：黄浦江一侧是外滩百年万国建筑，对岸是陆家嘴的现代天际线。弄堂里藏着小笼包与咖啡香，朱家角的水乡摇橹船则让人恍若隔世。',
        experiences: [
          { icon: '🌃', title: '外滩夜景', desc: '江畔漫步，一次看尽两岸天际线' },
          { icon: '🗼', title: '陆家嘴登高', desc: '上海中心观光厅俯瞰全城' },
          { icon: '🥟', title: '城隍庙小笼包', desc: '老字号的蟹粉小笼，先开窗后喝汤' },
          { icon: '🎢', title: '上海迪士尼', desc: '全球唯一疯狂动物城园区' }
        ],
        tips: [
          '外滩灯光秀通常 22:00 关闭，建议提早前往',
          '迪士尼建议提前一周购票并下载官方 App'
        ]
      },
      {
        id: 'xian',
        name: '西安',
        en: "Xi'an",
        tagline: '一眼千年，梦回大唐长安',
        image:
          'https://agent.qianwen.com/service/fec8273c-25ef-4b/4739fc217fb36537d3a287db2b73d1fb',
        bestSeason: '3-5月 / 9-11月',
        suggestDays: '3-4 天',
        intro:
          '西安是丝绸之路的起点、十三朝古都。秦始皇兵马俑诉说两千年前的帝国雄风，古城墙上可以骑行，夜晚的大唐不夜城灯火如昼，西北风味美食遍布街巷。',
        experiences: [
          { icon: '🗿', title: '秦始皇兵马俑', desc: '世界第八大奇迹，建议请讲解更有故事' },
          { icon: '🏮', title: '古城墙骑行', desc: '保存最完整的古代城墙，环骑 13.7 公里' },
          { icon: '🍜', title: '回民街美食', desc: '肉夹馍、biangbiang 面、羊肉泡馍' },
          { icon: '✨', title: '大唐不夜城', desc: '夜晚灯火通明，仿佛穿越回长安' }
        ],
        tips: [
          '兵马俑门票需实名预约，旺季建议提前 3 天',
          '景区讲解员或语音导览能让参观更有趣'
        ]
      },
      {
        id: 'chengdu',
        name: '成都',
        en: 'Chengdu',
        tagline: '天府之国，把节奏慢下来',
        image:
          'https://agent.qianwen.com/service/821166ac-10cd-4a/daee43ebece6de5ffe99351a096fd29f',
        bestSeason: '3-6月 / 9-11月',
        suggestDays: '3-5 天',
        intro:
          '成都有"天府之国"的美誉：上午看憨态可掬的大熊猫，下午在人民公园喝一碗盖碗茶，夜晚用一顿麻辣火锅收尾，感受"来了就不想走"的悠闲气质。',
        experiences: [
          { icon: '🐼', title: '大熊猫繁育基地', desc: '上午前往，看熊猫最活跃的时段' },
          { icon: '🍲', title: '川味火锅', desc: '地道麻辣，不能吃辣可选鸳鸯锅' },
          { icon: '🍵', title: '人民公园盖碗茶', desc: '竹椅上一坐半天，体验本地慢生活' },
          { icon: '🏔', title: '青城山与都江堰', desc: '世界文化遗产，高铁 30 分钟直达' }
        ],
        tips: [
          '熊猫基地节假日需提前预约',
          '辣度"微辣"已经是外国游客友好级别',
          '成都到青城山乘高铁约 30 分钟'
        ]
      }
    ],

    /* ---- 医疗服务（隐藏入口内展示） ---- */
    medicalServices: [
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
