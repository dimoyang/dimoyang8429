import 'export_saver_stub.dart' if (dart.library.html) 'export_saver_web.dart'
    as impl;

/// 把导出的 JSON 交付给用户。
///
/// Web 触发浏览器下载并返回 true；其余平台没有"无需额外权限即可保存到
/// 用户可见位置"的路径（移动端写应用私有目录用户也拿不到文件），
/// 因此返回 false，由 UI 降级为"预览 + 复制到剪贴板"。
Future<bool> saveExport(String json, {required String filename}) {
  return impl.saveExport(json, filename: filename);
}
