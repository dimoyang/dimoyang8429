import 'dart:convert';

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/network/api_service.dart';
import 'package:meditour_app/core/services/storage_service.dart';
import 'package:meditour_app/data/models/destination.dart';

/// 目的地仓库
///
/// 远程优先：从后端 /api/v1/destinations 拉取并持久化到本地；
/// 网络不可达时回退到持久缓存或内置示例数据，保证离线可用。
class DestinationRepository {
  DestinationRepository._();

  /// 内置示例数据（离线兜底，内容来源：设计稿定稿的示例数据）
  static const List<Destination> sampleDestinations = [
    Destination(
      id: 'beijing',
      name: '北京',
      nameEn: 'Beijing',
      tagline: '千年古都，历史与现代交汇',
      imageUrl:
          'https://agent.qianwen.com/service/37320046-bedd-4e/afbbffb6bdf6194f584bb626f1495045',
      searchTerms: [
        '北京',
        'Beijing',
        '长城',
        'Great Wall',
        'Große Mauer',
        'Grande Muraille',
        '故宫',
        'Forbidden City',
        'Verbotene Stadt',
        'Cité interdite',
        '烤鸭',
        'Peking duck',
        'Pekingente',
        'canard laqué',
      ],
      bestSeason: '4-5月 / 9-10月',
      suggestDays: '4-6 天',
      intro:
          '北京是中国的首都，拥有七处世界文化遗产。从故宫、长城到胡同四合院，三千年的历史层层展开，798 艺术区与三里屯又为它注入年轻的活力。',
      experiences: [
        DestinationExperience(
          icon: '🏯',
          title: '故宫漫步',
          description: '世界最大的宫殿建筑群，清晨入内光线最佳',
        ),
        DestinationExperience(
          icon: '🧗',
          title: '长城日出',
          description: '慕田峪长城人少景美，可乘缆车往返',
        ),
        DestinationExperience(
          icon: '🦆',
          title: '北京烤鸭',
          description: '百年老店品尝皮脆肉嫩的挂炉烤鸭',
        ),
        DestinationExperience(
          icon: '🛖',
          title: '胡同游',
          description: '乘人力车穿行小巷，体验老北京生活',
        ),
      ],
      tips: [
        '故宫门票需提前 7 天在官方小程序预约',
        '首都机场乘机场快轨 30 分钟直达市区',
        '春季偶有沙尘，建议随身备口罩',
      ],
    ),
    Destination(
      id: 'shanghai',
      name: '上海',
      nameEn: 'Shanghai',
      tagline: '东方巴黎，黄浦江畔的摩登风情',
      imageUrl:
          'https://agent.qianwen.com/service/678e78be-3b65-49/8f0b9c0d07d33d6b79c0d698b2bdaa8a',
      searchTerms: [
        '上海',
        'Shanghai',
        '外滩',
        'The Bund',
        'Bund',
        '豫园',
        'Yu Garden',
        'Jardin Yu',
        '小笼包',
        'xiaolongbao',
      ],
      bestSeason: '4-5月 / 10-11月',
      suggestDays: '3-4 天',
      intro:
          '上海是一座魔幻都市：黄浦江一侧是外滩百年万国建筑，对岸是陆家嘴的现代天际线。弄堂里藏着小笼包与咖啡香，朱家角的水乡摇橹船则让人恍若隔世。',
      experiences: [
        DestinationExperience(
          icon: '🌃',
          title: '外滩夜景',
          description: '江畔漫步，一次看尽两岸天际线',
        ),
        DestinationExperience(
          icon: '🗼',
          title: '陆家嘴登高',
          description: '上海中心观光厅俯瞰全城',
        ),
        DestinationExperience(
          icon: '🥟',
          title: '城隍庙小笼包',
          description: '老字号的蟹粉小笼，先开窗后喝汤',
        ),
        DestinationExperience(
          icon: '🎢',
          title: '上海迪士尼',
          description: '全球唯一疯狂动物城园区',
        ),
      ],
      tips: [
        '外滩灯光秀通常 22:00 关闭，建议提早前往',
        '迪士尼建议提前一周购票并下载官方 App',
      ],
    ),
    Destination(
      id: 'xian',
      name: '西安',
      nameEn: "Xi'an",
      tagline: '一眼千年，梦回大唐长安',
      imageUrl:
          'https://agent.qianwen.com/service/fec8273c-25ef-4b/4739fc217fb36537d3a287db2b73d1fb',
      searchTerms: [
        '西安',
        "Xi'an",
        '兵马俑',
        'Terracotta Warriors',
        'Terrakotta-Armee',
        'armée de terre cuite',
        '城墙',
        'city wall',
        'Stadtmauer',
        'muraille',
        '回民街',
        'Muslim Quarter',
      ],
      bestSeason: '3-5月 / 9-11月',
      suggestDays: '3-4 天',
      intro:
          '西安是丝绸之路的起点、十三朝古都。秦始皇兵马俑诉说两千年前的帝国雄风，古城墙上可以骑行，夜晚的大唐不夜城灯火如昼，西北风味美食遍布街巷。',
      experiences: [
        DestinationExperience(
          icon: '🗿',
          title: '秦始皇兵马俑',
          description: '世界第八大奇迹，建议请讲解更有故事',
        ),
        DestinationExperience(
          icon: '🏮',
          title: '古城墙骑行',
          description: '保存最完整的古代城墙，环骑 13.7 公里',
        ),
        DestinationExperience(
          icon: '🍜',
          title: '回民街美食',
          description: '肉夹馍、biangbiang 面、羊肉泡馍',
        ),
        DestinationExperience(
          icon: '✨',
          title: '大唐不夜城',
          description: '夜晚灯火通明，仿佛穿越回长安',
        ),
      ],
      tips: [
        '兵马俑门票需实名预约，旺季建议提前 3 天',
        '景区讲解员或语音导览能让参观更有趣',
      ],
    ),
    Destination(
      id: 'chengdu',
      name: '成都',
      nameEn: 'Chengdu',
      tagline: '天府之国，把节奏慢下来',
      imageUrl:
          'https://agent.qianwen.com/service/821166ac-10cd-4a/daee43ebece6de5ffe99351a096fd29f',
      searchTerms: [
        '成都',
        'Chengdu',
        '熊猫',
        'panda',
        '火锅',
        'hot pot',
        'Feuertopf',
        'fondue chinoise',
        '茶馆',
        'teahouse',
        'Teehaus',
        'maison de thé',
      ],
      bestSeason: '3-6月 / 9-11月',
      suggestDays: '3-5 天',
      intro:
          '成都有"天府之国"的美誉：上午看憨态可掬的大熊猫，下午在人民公园喝一碗盖碗茶，夜晚用一顿麻辣火锅收尾，感受"来了就不想走"的悠闲气质。',
      experiences: [
        DestinationExperience(
          icon: '🐼',
          title: '大熊猫繁育基地',
          description: '上午前往，看熊猫最活跃的时段',
        ),
        DestinationExperience(
          icon: '🍲',
          title: '川味火锅',
          description: '地道麻辣，不能吃辣可选鸳鸯锅',
        ),
        DestinationExperience(
          icon: '🍵',
          title: '人民公园盖碗茶',
          description: '竹椅上一坐半天，体验本地慢生活',
        ),
        DestinationExperience(
          icon: '🏔',
          title: '青城山与都江堰',
          description: '世界文化遗产，高铁 30 分钟直达',
        ),
      ],
      tips: [
        '熊猫基地节假日需提前预约',
        '辣度"微辣"已经是外国游客友好级别',
        '成都到青城山乘高铁约 30 分钟',
      ],
    ),
  ];

  /// 首页首屏主图（长城，内容来源：设计稿定稿的示例数据）
  static const String heroImageUrl =
      'https://agent.qianwen.com/service/e2da4fa3-c27e-4f/832861465aa0afce641df2da4babbb2c';

  static List<Destination> _cache = sampleDestinations;
  static bool _lastLoadWasSample = false;

  /// 最近一次远程拉取是否回退到了示例/缓存数据（用于 UI 离线提示）。
  static bool get lastLoadWasSample => _lastLoadWasSample;

  /// 仅测试用：重置缓存与回退标记，返回重置后的样例列表。
  @visibleForTesting
  static List<Destination> resetForTesting() {
    _cache = sampleDestinations;
    _lastLoadWasSample = false;
    return List.unmodifiable(_cache);
  }

  /// 启动时恢复上次成功拉取的持久缓存；无缓存或解析失败时保持示例数据。
  ///
  /// 返回恢复后的列表，调用方无需再读取仓储内部状态。
  static Future<List<Destination>> restoreCache() async {
    final raw = await StorageService.getCachedDestinations();
    if (raw == null || raw.isEmpty) {
      return List.unmodifiable(_cache);
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        final restored = decoded
            .whereType<Map>()
            .map(
                (item) => Destination.fromJson(Map<String, dynamic>.from(item)))
            .toList();
        if (restored.isNotEmpty) {
          _cache = restored;
        }
      }
    } on FormatException {
      // 缓存损坏时忽略，保持示例数据。
    }
    return List.unmodifiable(_cache);
  }

  /// 远程拉取最新目的地列表。
  ///
  /// 成功：替换缓存并持久化；
  /// 网络不可达/超时：保留现有缓存并置 [lastLoadWasSample]；
  /// HTTP 4xx/5xx 抛 [ApiException]，解析失败抛 [ResponseParseException]，不回退。
  static Future<List<Destination>> refresh({String? lang}) async {
    try {
      final data = await ApiService.instance.getDestinations(lang: lang);
      final loaded = <Destination>[];
      for (final item in data) {
        try {
          loaded.add(Destination.fromJson(item, lang: lang));
        } on TypeError {
          throw const ResponseParseException();
        }
      }
      _cache = loaded;
      _lastLoadWasSample = false;
      await StorageService.setCachedDestinations(
        jsonEncode(loaded.map((item) => item.toJson()).toList()),
      );
      return List.unmodifiable(_cache);
    } on NetworkException {
      _lastLoadWasSample = true;
      return List.unmodifiable(_cache);
    }
  }
}
