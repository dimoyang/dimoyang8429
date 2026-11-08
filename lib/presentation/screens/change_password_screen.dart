import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/utils/route_location.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/app_toast.dart';
import 'package:meditour_app/presentation/widgets/form_field.dart';
import 'package:provider/provider.dart';

/// 修改密码。
///
/// 成功后后端让所有旧令牌失效，这里主动清会话并引导重新登录；
/// 登录页会带上调用方传入的 redirect，回到用户原本所在的位置。
class ChangePasswordScreen extends StatefulWidget {
  final String? redirect;

  const ChangePasswordScreen({super.key, this.redirect});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _currentController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _submitting = false;

  String? get _safeRedirect {
    final redirect = widget.redirect;
    return (redirect != null && redirect.startsWith('/')) ? redirect : null;
  }

  @override
  void dispose() {
    _currentController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.changePasswordTitle)),
      body: SafeArea(
        top: false,
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
            children: [
              AppFormField(
                label: l10n.changePasswordCurrentLabel,
                controller: _currentController,
                obscureText: true,
                textInputAction: TextInputAction.next,
                validator: (v) =>
                    (v == null || v.isEmpty) ? l10n.passwordError : null,
              ),
              const SizedBox(height: 14),
              AppFormField(
                label: l10n.newPasswordLabel,
                controller: _passwordController,
                obscureText: true,
                textInputAction: TextInputAction.next,
                validator: (v) =>
                    (v == null || v.length < 6) ? l10n.passwordError : null,
              ),
              const SizedBox(height: 14),
              AppFormField(
                label: l10n.passwordConfirmLabel,
                controller: _confirmController,
                obscureText: true,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submit(),
                validator: (v) => (v == null || v != _passwordController.text)
                    ? l10n.passwordMismatch
                    : null,
              ),
              const SizedBox(height: 24),
              FilledButton(
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
                onPressed: _submitting ? null : _submit,
                child: _submitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Text(
                        l10n.changePasswordButton,
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w700),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (_submitting) {
      return;
    }
    final l10n = AppLocalizations.of(context);
    FocusScope.of(context).unfocus();
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() => _submitting = true);
    try {
      await context.read<AuthProvider>().changePassword(
            currentPassword: _currentController.text,
            newPassword: _passwordController.text,
          );
      if (!mounted) {
        return;
      }
      await _showReLoginDialog(l10n.changePasswordSuccess);
    } on ApiBusinessException catch (e) {
      if (!mounted) {
        return;
      }
      // 400 表示当前密码错误，和网络失败/服务端错误区分提示。
      _showError(
        e.statusCode == 400
            ? l10n.changePasswordWrongCurrent
            : e.toLocalizedMessage(l10n),
      );
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      _showError(e.toLocalizedMessage(l10n));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _showError(String message) {
    AppToast.error(context, message);
  }

  Future<void> _showReLoginDialog(String message) async {
    final l10n = AppLocalizations.of(context);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        content: Text(message),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              if (mounted) {
                context.go(loginLocation(redirect: _safeRedirect));
              }
            },
            child: Text(l10n.loginButton),
          ),
        ],
      ),
    );
  }
}
