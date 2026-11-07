import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/utils/validators.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/form_field.dart';
import 'package:provider/provider.dart';

/// 注册页
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.registerTitle)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            AppFormField(
              label: l10n.fullNameLabel,
              controller: _nameController,
            ),
            const SizedBox(height: 14),
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
              validator: (v) => (v == null || v.length < 6)
                  ? l10n.passwordError
                  : null,
            ),
            const SizedBox(height: 14),
            AppFormField(
              label: l10n.passwordConfirmLabel,
              controller: _confirmController,
              obscureText: true,
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
                      l10n.registerButton,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700),
                    ),
            ),
            const SizedBox(height: 14),
            Center(
              child: TextButton(
                onPressed: _submitting ? null : () => context.pop(),
                child: Text(
                  l10n.registerSwitchToLogin,
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
      final langCode = Localizations.localeOf(context).languageCode;
      await context.read<AuthProvider>().register(
            email: _emailController.text.trim(),
            password: _passwordController.text,
            fullName: _nameController.text.trim(),
            preferredLanguage: langCode,
          );
      if (!mounted) {
        return;
      }
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/profile');
      }
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toLocalizedMessage(l10n)),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }
}
