/// 登录用户信息（对应后端 UserResponse）。
class UserProfile {
  final int id;
  final String email;
  final String? fullName;
  final String? phone;
  final String preferredLanguage;

  const UserProfile({
    required this.id,
    required this.email,
    this.fullName,
    this.phone,
    this.preferredLanguage = 'en',
  });

  /// 展示名称：优先全名，其次邮箱。
  String get displayName =>
      (fullName != null && fullName!.isNotEmpty) ? fullName! : email;

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String?,
      phone: json['phone'] as String?,
      preferredLanguage: json['preferred_language'] as String? ?? 'en',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'phone': phone,
      'preferred_language': preferredLanguage,
    };
  }
}
