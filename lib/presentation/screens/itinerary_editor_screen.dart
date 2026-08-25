import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/travel_itinerary.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart';

/// Creates or edits a locally saved itinerary.
class ItineraryEditorScreen extends StatefulWidget {
  final String? itineraryId;

  const ItineraryEditorScreen({super.key, this.itineraryId});

  @override
  State<ItineraryEditorScreen> createState() => _ItineraryEditorScreenState();
}

class _ItineraryEditorScreenState extends State<ItineraryEditorScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _notesController = TextEditingController();
  final Set<String> _destinationIds = {};

  DateTimeRange? _dateRange;
  TravelItinerary? _existingItinerary;
  bool _initialized = false;
  bool _submitted = false;
  bool _saving = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_initialized) {
      return;
    }

    final provider = context.watch<ItineraryProvider>();
    if (!provider.isLoaded) {
      return;
    }

    if (widget.itineraryId != null) {
      _existingItinerary = provider.findById(widget.itineraryId!);
      final itinerary = _existingItinerary;
      if (itinerary != null) {
        _titleController.text = itinerary.title;
        _notesController.text = itinerary.notes;
        _destinationIds.addAll(itinerary.destinationIds);
        _dateRange = DateTimeRange(
          start: itinerary.startDate,
          end: itinerary.endDate,
        );
      }
    }
    _initialized = true;
  }

  @override
  void dispose() {
    _titleController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final provider = context.watch<ItineraryProvider>();

    if (!provider.isLoaded || !_initialized) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            widget.itineraryId == null
                ? l10n.itineraryCreateTitle
                : l10n.itineraryEditTitle,
          ),
        ),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (widget.itineraryId != null && _existingItinerary == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.itineraryEditTitle)),
        body: Center(child: Text(l10n.itineraryNotFound)),
      );
    }

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(
          _existingItinerary == null
              ? l10n.itineraryCreateTitle
              : l10n.itineraryEditTitle,
        ),
      ),
      body: SafeArea(
        top: false,
        child: Form(
          key: _formKey,
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: ListView(
                padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
                children: [
                  _SectionLabel(text: l10n.itineraryNameLabel),
                  TextFormField(
                    key: const Key('itineraryTitleField'),
                    controller: _titleController,
                    textInputAction: TextInputAction.next,
                    validator: (value) => value == null || value.trim().isEmpty
                        ? l10n.itineraryNameError
                        : null,
                    decoration: _inputDecoration(l10n.itineraryNameHint),
                  ),
                  const SizedBox(height: 20),
                  _SectionLabel(text: l10n.itineraryDestinationsLabel),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(
                        color: _submitted && _destinationIds.isEmpty
                            ? AppColors.danger
                            : AppColors.line,
                      ),
                    ),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: DestinationRepository.destinations.map((item) {
                        final selected = _destinationIds.contains(item.id);
                        return FilterChip(
                          key: Key('destinationChip_${item.id}'),
                          selected: selected,
                          label: Text(
                            item.getName(
                              Localizations.localeOf(context).languageCode,
                            ),
                          ),
                          avatar: Icon(
                            selected ? Icons.check : Icons.location_on_outlined,
                            size: 18,
                          ),
                          onSelected: (value) {
                            setState(() {
                              if (value) {
                                _destinationIds.add(item.id);
                              } else {
                                _destinationIds.remove(item.id);
                              }
                            });
                          },
                        );
                      }).toList(),
                    ),
                  ),
                  if (_submitted && _destinationIds.isEmpty)
                    _FieldError(text: l10n.itineraryDestinationsError),
                  const SizedBox(height: 20),
                  _SectionLabel(text: l10n.itineraryDatesLabel),
                  InkWell(
                    key: const Key('itineraryDateField'),
                    borderRadius: BorderRadius.circular(8),
                    onTap: _pickDates,
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 54),
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: _submitted && _dateRange == null
                              ? AppColors.danger
                              : AppColors.line,
                        ),
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.date_range_outlined,
                            color: AppColors.primary,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              _dateRange == null
                                  ? l10n.itineraryDatesHint
                                  : _formatDateRange(context, _dateRange!),
                              style: TextStyle(
                                color: _dateRange == null
                                    ? AppColors.ink3
                                    : AppColors.ink,
                              ),
                            ),
                          ),
                          const Icon(
                            Icons.chevron_right,
                            color: AppColors.ink3,
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (_submitted && _dateRange == null)
                    _FieldError(text: l10n.itineraryDatesError),
                  const SizedBox(height: 20),
                  _SectionLabel(text: l10n.itineraryNotesLabel),
                  TextFormField(
                    key: const Key('itineraryNotesField'),
                    controller: _notesController,
                    minLines: 3,
                    maxLines: 6,
                    decoration: _inputDecoration(l10n.itineraryNotesHint),
                  ),
                  const SizedBox(height: 28),
                  FilledButton.icon(
                    key: const Key('itinerarySaveButton'),
                    onPressed: _saving ? null : _save,
                    icon: _saving
                        ? const SizedBox.square(
                            dimension: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.check),
                    label: Text(l10n.itinerarySave),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.line),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.primary, width: 1.5),
      ),
    );
  }

  Future<void> _pickDates() async {
    final now = DateUtils.dateOnly(DateTime.now());
    final initialRange = _dateRange ??
        DateTimeRange(
          start: now.add(const Duration(days: 30)),
          end: now.add(const Duration(days: 36)),
        );
    final picked = await showDateRangePicker(
      context: context,
      initialDateRange: initialRange,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 5, 12, 31),
    );

    if (picked != null && mounted) {
      setState(() => _dateRange = picked);
    }
  }

  String _formatDateRange(BuildContext context, DateTimeRange range) {
    final localizations = MaterialLocalizations.of(context);
    return '${localizations.formatMediumDate(range.start)} - '
        '${localizations.formatMediumDate(range.end)}';
  }

  Future<void> _save() async {
    setState(() => _submitted = true);
    if (!_formKey.currentState!.validate() ||
        _destinationIds.isEmpty ||
        _dateRange == null) {
      return;
    }

    setState(() => _saving = true);
    final provider = context.read<ItineraryProvider>();
    final range = _dateRange!;
    final existing = _existingItinerary;

    if (existing == null) {
      await provider.create(
        title: _titleController.text.trim(),
        startDate: range.start,
        endDate: range.end,
        destinationIds: _destinationIds.toList(),
        notes: _notesController.text.trim(),
      );
    } else {
      await provider.update(
        existing.copyWith(
          title: _titleController.text.trim(),
          startDate: range.start,
          endDate: range.end,
          destinationIds: _destinationIds.toList(),
          notes: _notesController.text.trim(),
        ),
      );
    }

    if (mounted) {
      context.pop(true);
    }
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;

  const _SectionLabel({required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        text,
        style: const TextStyle(
          color: AppColors.ink,
          fontSize: 14,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _FieldError extends StatelessWidget {
  final String text;

  const _FieldError({required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 12, top: 6),
      child: Text(
        text,
        style: const TextStyle(color: AppColors.danger, fontSize: 12),
      ),
    );
  }
}
