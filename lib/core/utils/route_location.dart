/// 统一生成登录页地址。
///
/// `redirect` 只接受站内绝对路径（以 `/` 开头），避免开放重定向；
/// 登录成功后由登录页按同一语义回跳，避免用户本来要去别处却被送回首页。
String loginLocation({String? redirect}) {
  final safeRedirect =
      (redirect != null && redirect.startsWith('/')) ? redirect : null;
  if (safeRedirect == null) {
    return '/login';
  }
  return '/login?redirect=${Uri.encodeQueryComponent(safeRedirect)}';
}
