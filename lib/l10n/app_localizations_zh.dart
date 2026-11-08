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
  String get bookingNote => '🔒 您的信息仅用于本次预约对接，医疗顾问将在 24 小时内与您联系。';

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
  String startingFrom(String price) {
    return '$price 起';
  }

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

  @override
  String get profileBookings => '我的预约';

  @override
  String get profileBookingsSub => '查看医疗服务预约记录';

  @override
  String get bookingsLoginBody => '登录后可查看您的预约记录与就诊信息。';

  @override
  String get bookingsEmptyTitle => '还没有预约';

  @override
  String get bookingsEmptyBody => '您提交的医疗服务预约会显示在这里。';

  @override
  String get bookingsLoadFailed => '预约加载失败';

  @override
  String get bookingsAppointmentDate => '到诊日期';

  @override
  String get bookingsStatusPending => '待确认';

  @override
  String get bookingsStatusConfirmed => '已确认';

  @override
  String get bookingsStatusCompleted => '已完成';

  @override
  String get bookingsStatusCancelled => '已取消';

  @override
  String get bookingsStatusUnknown => '未知状态';

  @override
  String get bookingsCreatedAt => '下单时间';

  @override
  String get bookingsCancel => '取消预约';

  @override
  String get bookingsCancelTitle => '取消预约';

  @override
  String get bookingsCancelBody => '取消后无法恢复，确定要取消这笔预约吗？';

  @override
  String get bookingsCancelConfirm => '确认取消';

  @override
  String get bookingsCancelDismiss => '保留';

  @override
  String get bookingsCancelSuccess => '预约已取消';

  @override
  String get bookingsCancelNotFound => '预约不存在或无权操作';

  @override
  String get bookingsCancelConflict => '该预约当前状态不可取消';

  @override
  String get destinationSearchTitle => '搜索目的地';

  @override
  String get destinationFilterAll => '全部';

  @override
  String get destinationFilterFavorites => '已收藏';

  @override
  String get clearSearch => '清空搜索';

  @override
  String get searchNoResultsTitle => '没有找到目的地';

  @override
  String get searchNoResultsBody => '试试其他城市、景点或美食关键词。';

  @override
  String get favoriteEmptyTitle => '还没有收藏';

  @override
  String get favoriteEmptyBody => '点击目的地上的爱心，即可在这里快速找到。';

  @override
  String get addToFavorites => '收藏目的地';

  @override
  String get removeFromFavorites => '取消收藏';

  @override
  String get itineraryCreateTitle => '创建行程';

  @override
  String get itineraryEditTitle => '编辑行程';

  @override
  String get itineraryNotFound => '未找到该行程';

  @override
  String get itineraryNewButton => '新建行程';

  @override
  String get itineraryNameLabel => '行程名称';

  @override
  String get itineraryNameHint => '例如：中国春日之旅';

  @override
  String get itineraryNameError => '请输入行程名称';

  @override
  String get itineraryDestinationsLabel => '目的地';

  @override
  String get itineraryDestinationsError => '请至少选择一个目的地';

  @override
  String get itineraryDatesLabel => '旅行日期';

  @override
  String get itineraryDatesHint => '选择出发和结束日期';

  @override
  String get itineraryDatesError => '请选择旅行日期';

  @override
  String get itineraryDayPlanLabel => '按天安排';

  @override
  String get itineraryDayPlanHint => '先选择旅行日期，再安排每天的地点。';

  @override
  String itineraryDayLabel(int day) {
    return '第 $day 天';
  }

  @override
  String get itineraryDayNotesHint => '当天的安排或备注';

  @override
  String get itineraryAddPlace => '添加地点';

  @override
  String get itinerarySelectPlace => '选择地点';

  @override
  String get itineraryNoPlacesInDay => '当天还没有安排地点';

  @override
  String get itineraryMoveUp => '上移';

  @override
  String get itineraryMoveDown => '下移';

  @override
  String get itineraryRemovePlace => '移除地点';

  @override
  String get itineraryNotesLabel => '行程备注';

  @override
  String get itineraryNotesHint => '记录交通、酒店、想去的地点或其他安排';

  @override
  String get itinerarySave => '保存行程';

  @override
  String get itineraryActions => '行程操作';

  @override
  String get itineraryEditAction => '编辑';

  @override
  String get itineraryDeleteAction => '删除';

  @override
  String get itineraryDeleteTitle => '删除这份行程？';

  @override
  String get itineraryDeleteBody => '这份已保存的行程将从当前设备中删除。';

  @override
  String get cancel => '取消';

  @override
  String itineraryDays(int days) {
    return '$days 天';
  }

  @override
  String get addToTripCreateNew => '新建行程并加入';

  @override
  String get addToTripAdded => '已加入行程';

  @override
  String get profileAccount => '账号';

  @override
  String get loginTitle => '登录';

  @override
  String get registerTitle => '注册账号';

  @override
  String get emailLabel => '邮箱';

  @override
  String get emailError => '请输入有效的邮箱地址';

  @override
  String get passwordLabel => '密码';

  @override
  String get passwordError => '密码至少 6 位';

  @override
  String get passwordConfirmLabel => '确认密码';

  @override
  String get passwordMismatch => '两次输入的密码不一致';

  @override
  String get fullNameLabel => '姓名（选填）';

  @override
  String get loginButton => '登录';

  @override
  String get registerButton => '注册';

  @override
  String get loginSwitchToRegister => '还没有账号？去注册';

  @override
  String get registerSwitchToLogin => '已有账号？去登录';

  @override
  String get logout => '退出登录';

  @override
  String get loginEntrySub => '登录后可预约医疗服务';

  @override
  String get loginRequiredTitle => '需要登录';

  @override
  String get loginRequiredBody => '提交预约前，请先登录或注册账号。';

  @override
  String get goLogin => '去登录';

  @override
  String get formPhone => '手机号';

  @override
  String get formPhoneError => '请输入有效的手机号';

  @override
  String get formEmail => '邮箱';

  @override
  String get formEmailError => '请输入有效的邮箱地址';

  @override
  String get formDateError => '请选择期望到诊日期';

  @override
  String get extrasTitle => '附加服务';

  @override
  String get needTranslator => '翻译陪同';

  @override
  String get needAccommodation => '住宿安排';

  @override
  String get needPickup => '接机服务';

  @override
  String get bookingTotal => '合计';

  @override
  String get bookingPackageNotFound => '该服务已下架，请返回重新选择。';

  @override
  String get errorNetwork => '网络不可用，请检查连接后重试。';

  @override
  String get errorUnauthorized => '登录已过期，请重新登录。';

  @override
  String get errorInvalidCredentials => '邮箱或密码错误。';

  @override
  String get errorServer => '服务器繁忙，请稍后重试。';

  @override
  String get errorUnknown => '操作失败，请重试。';

  @override
  String get errorRequest => '请求未能完成，请检查填写的信息后重试。';

  @override
  String get medicalOfflineHint => '暂时无法连接服务器，当前显示的是示例数据。';

  @override
  String get medicalLoadFailed => '加载失败';

  @override
  String get medicalEmptyTitle => '暂无可预约服务';

  @override
  String get medicalEmptyBody => '当前没有可展示的医疗服务，请稍后重试。';

  @override
  String get retry => '重试';
}
