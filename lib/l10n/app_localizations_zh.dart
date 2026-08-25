// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appTitle => '医旅';

  @override
  String get appSubtitle => '中国旅行一站式平台';

  @override
  String get tagline => '从欧洲出发，遇见中国';

  @override
  String get taglineSubtitle => '五千年文明，等你来探索';

  @override
  String get searchHint => '搜索目的地、景点、美食…';

  @override
  String get searchComingSoon => '搜索功能将在下一版本上线';

  @override
  String get heroTitle => '登长城 · 逛故宫 · 吃火锅';

  @override
  String get heroSubtitle => '签证协助 · 交通预订 · 行程定制，一站搞定';

  @override
  String get chipVisa => '签证协助';

  @override
  String get chipTransport => '高铁与机票';

  @override
  String get chipHotel => '酒店预订';

  @override
  String get chipItinerary => '行程定制';

  @override
  String get chipComingSoon => '服务将在下一版本上线';

  @override
  String get sectionDestinations => '热门目的地';

  @override
  String get sectionDestinationsSub => '4 座城市精选';

  @override
  String get sectionTips => '旅行小贴士';

  @override
  String get tipPayment => '中国已全面普及移动支付，机场可兑换少量现金应急，大型酒店与免税店支持外卡';

  @override
  String get tipSim => '建议出发前办好中国手机卡或 eSIM，方便扫码乘车、翻译导航';

  @override
  String get medicalEntryTitle => '特色服务 · 健康之旅';

  @override
  String get medicalEntrySub => '旅途中如有医疗照护需求，我们为您妥善安排';

  @override
  String get footerText => '医旅 Meditour · 让每一次中国之旅都安心';

  @override
  String get homeAppBarTitle => '发现中国';

  @override
  String get medicalListTitle => '健康之旅';

  @override
  String get medicalListInfo =>
      '如果您在旅途中有医疗照护需求，我们可以为您对接优质医疗资源；若暂无需要，欢迎随时回来继续探索旅程。';

  @override
  String get destinationNotFound => '未找到该目的地';

  @override
  String get serviceNotFound => '未找到该服务';

  @override
  String get sectionImpression => '城市印象';

  @override
  String get sectionExperiences => '必玩体验';

  @override
  String get sectionTravelTips => '旅行贴士';

  @override
  String get sectionIntro => '服务简介';

  @override
  String get sectionHighlights => '服务亮点';

  @override
  String get sectionProcess => '就诊流程';

  @override
  String get statBestSeason => '最佳季节';

  @override
  String get statSuggestDays => '建议游玩';

  @override
  String get statBasePrice => '起步价格';

  @override
  String get statDuration => '疗程天数';

  @override
  String get statCompanion => '顾问陪同';

  @override
  String get btnItinerary => '咨询行程定制';

  @override
  String get btnBookConsult => '预约咨询';

  @override
  String get btnSubmit => '提交预约';

  @override
  String get btnBackHome => '返回首页';

  @override
  String get btnViewService => '查看服务详情';

  @override
  String get itineraryComingSoon => '行程定制咨询将在下一版本上线';

  @override
  String get bookingSuccess => '预约提交成功';

  @override
  String get bookingSuccessDesc => '感谢您的信任！医疗顾问将在 24 小时内通过您预留的联系方式与您确认行程细节。';

  @override
  String get bookingNo => '预约编号';

  @override
  String get bookingNote =>
      '🔒 您的信息仅用于本次预约对接，医疗顾问将在 24 小时内与您联系。本设计稿中的提交流程为前端演示，不连接真实服务。';

  @override
  String get formName => '姓名';

  @override
  String get formNameError => '请输入姓名';

  @override
  String get formContact => '联系方式（邮箱 / 电话）';

  @override
  String get formContactHint => '用于顾问与您确认行程';

  @override
  String get formContactError => '请输入有效的联系方式';

  @override
  String get formDate => '期望到诊日期';

  @override
  String get formDateHint => '请选择日期';

  @override
  String get formNote => '病情 / 需求说明';

  @override
  String get formNoteHint => '简要描述您的健康状况与需求（选填）';

  @override
  String daysTreatment(int days) {
    return '$days 天治疗';
  }

  @override
  String get hospitalLabel => '医院';

  @override
  String get priceLabel => '基础价格';

  @override
  String get durationLabel => '疗程时长';

  @override
  String get startingFrom => '起';

  @override
  String get level3A => '三级甲等';

  @override
  String get navDiscover => '发现';

  @override
  String get navItinerary => '行程';

  @override
  String get navTravelTools => '旅行工具';

  @override
  String get navProfile => '我的';

  @override
  String get itineraryTitle => '我的行程';

  @override
  String get itineraryEmptyTitle => '还没有行程';

  @override
  String get itineraryEmptyBody => '收藏或规划的中国旅行行程会显示在这里。';

  @override
  String get travelToolsTitle => '旅行工具';

  @override
  String get travelToolsIntro => '准备入境中国和旅途中经常用到的实用信息。';

  @override
  String get toolVisaTitle => '签证与入境';

  @override
  String get toolVisaSummary => '证件要求与抵达准备';

  @override
  String get toolVisaDetail =>
      '入境政策会因国籍、旅行证件和路线而异。预订前请向中国使领馆核对最新要求，并同时保存护照、签证、住宿和返程行程的电子及纸质副本。';

  @override
  String get toolPaymentTitle => '支付准备';

  @override
  String get toolPaymentSummary => '银行卡、移动支付与备用现金';

  @override
  String get toolPaymentDetail =>
      '出发前请向发卡银行确认境外支付能力。建议准备至少一张国际银行卡和少量现金，并提前完成可能需要的移动支付设置。';

  @override
  String get toolTransportTitle => '高铁与市内交通';

  @override
  String get toolTransportSummary => '购票、车站与证件核验';

  @override
  String get toolTransportDetail =>
      '高铁票通常与购票时使用的护照绑定。请为证件核验预留时间，确认完整车站名称，并在乘车时携带护照原件。';

  @override
  String get toolInternetTitle => '网络与手机卡';

  @override
  String get toolInternetSummary => '国际漫游、eSIM 与联网准备';

  @override
  String get toolInternetDetail =>
      '可在抵达前准备国际漫游或 eSIM，也可在落地后办理本地手机卡。建议提前下载重要旅行资料和离线翻译，以便网络受限时使用。';

  @override
  String get profileTitle => '我的';

  @override
  String get profilePreferences => '偏好设置';

  @override
  String get profileLanguage => '语言';

  @override
  String get profileMoreAssistance => '更多协助';

  @override
  String get profileAbout => '关于';

  @override
  String get profileAppVersion => '应用版本';

  @override
  String get profileLicenses => '开源许可';
}
