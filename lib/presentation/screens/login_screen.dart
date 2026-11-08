import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/utils/validators.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/app_toast.dart';
import 'package:meditour_app/presentation/widgets/form_field.dart';
import 'package:provider/provider.dart';

/// 登录页
class LoginScreen extends StatefulWidget {
  final String? redirect;

  const LoginScreen({super.key, this.redirect});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.loginTitle)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            AppFormField(
              label: l10n.emailLabel,
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              validator: (v) =>
                  Validators.isValidEmail(v) ? null : l10n.emailError,
            ),
            const SizedBox(height: 14),
            AppFormField(
              label: l10n.passwordLabel,
              controller: _passwordController,
              obscureText: true,
              validator: (v) =>
                  (v == null || v.length < 6) ? l10n.passwordError : null,
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
                      l10n.loginButton,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700),
                    ),
            ),
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _submitting ? null : _openForgotPassword,
                child: Text(
                  l10n.loginForgotPassword,
                  style: const TextStyle(
                    fontSize: 13.5,
                    color: AppColors.primaryDark,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Center(
              child: TextButton(
                onPressed:
                    _submitting ? null : () => context.pushNamed('register'),
                child: Text(
                  l10n.loginSwitchToRegister,
                  style: const TextStyle(
                    fontSize: 13.5,
                    color: AppColors.primaryDark,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context);
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() => _submitting = true);
    try {
      await context.read<AuthProvider>().login(
            email: _emailController.text.trim(),
            password: _passwordController.text,
          );
      if (!mounted) {
        return;
      }
      _navigateBack();
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      AppToast.error(context, e.toLocalizedMessage(l10n));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _openForgotPassword() {
    final redirect = widget.redirect;
    // 忘记密码/重置密码成功后仍需登录；把原本要去的站内路径一路带下去。
    final safeRedirect =
        (redirect != null && redirect.startsWith('/')) ? redirect : null;
    context.pushNamed(
      'forgotPassword',
      queryParameters: {if (safeRedirect != null) 'redirect': safeRedirect},
    );
  }

  void _navigateBack() {
    final redirect = widget.redirect;
    if (redirect != null && redirect.startsWith('/')) {
      context.go(redirect);
      return;
    }
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/profile');
    }
  }
}
