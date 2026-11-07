/// 表单校验器
class Validators {
  Validators._();

  /// 必填校验
  static String? required(String? value, String message) {
    if (value == null || value.trim().isEmpty) {
      return message;
    }
    return null;
  }

  /// 联系方式校验：邮箱（含 @）或电话号码
  static String? contact(String? value, String message) {
    if (!isValidContact(value)) {
      return message;
    }
    return null;
  }

  /// 联系方式是否有效（邮箱或电话）
  static bool isValidContact(String? value) {
    final v = (value ?? '').trim();
    if (v.length < 5) {
      return false;
    }
    final isEmailLike = v.contains('@');
    final isPhoneLike = RegExp(r'^[+\d][\d\s-]{4,}$').hasMatch(v);
    return isEmailLike || isPhoneLike;
  }

  /// 邮箱是否有效
  static bool isValidEmail(String? value) {
    final v = (value ?? '').trim();
    return RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(v);
  }

  /// 电话号码是否有效
  static bool isValidPhone(String? value) {
    final v = (value ?? '').trim();
    return RegExp(r'^[+\d][\d\s-]{4,}$').hasMatch(v);
  }

  /// 日期校验：允许为空；填写时必须晚于今天
  static String? futureDate(String? value, String message) {
    if (value == null || value.isEmpty) {
      return null;
    }
    final picked = DateTime.tryParse(value);
    if (picked == null) {
      return message;
    }
    final today = DateTime.now();
    final todayMidnight = DateTime(today.year, today.month, today.day);
    if (!picked.isAfter(todayMidnight)) {
      return message;
    }
    return null;
  }
}
