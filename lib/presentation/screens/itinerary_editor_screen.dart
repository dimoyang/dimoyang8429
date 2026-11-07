import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/data/models/travel_itinerary.dart';
import 'package:meditour_app/data/respositories/destination_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
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
  List<ItineraryDay> _dayPlans = [];

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
        _dayPlans = _buildDayPlans(
          itinerary.dayCount,
          existing: itinerary.days,
        );
        if (itinerary.days.isEmpty && _dayPlans.isNotEmpty) {
          _dayPlans[0] = _dayPlans[0].copyWith(
            destinationIds: itinerary.destinationIds
                .where(_destinationIds.contains)
                .toList(),
          );
        }
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
    final languageCode = Localizations.localeOf(context).languageCode;
    final destinationNames = {
      for (final destination in DestinationRepository.destinations)
        destination.id: destination.getName(languageCode),
    };

    if (provider.loadFailed) {
      return Scaffold(
        appBar: AppBar(
          title: Text(
            widget.itineraryId == null
                ? l10n.itineraryCreateTitle
                : l10n.itineraryEditTitle,
          ),
        ),
        body: ErrorState(
          icon: Icons.route_outlined,
          title: l10n.medicalLoadFailed,
          message: l10n.errorUnknown,
          onRetry: provider.load,
        ),
      );
    }

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
                                _dayPlans = _dayPlans
                                    .map(
                                      (day) => day.copyWith(
                                        destinationIds: day.destinationIds
                                            .where((id) => id != item.id)
                                            .toList(),
                                      ),
                                    )
                                    .toList();
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
                  _SectionLabel(text: l10n.itineraryDayPlanLabel),
                  if (_dateRange == null)
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: AppColors.line),
                      ),
                      child: Text(
                        l10n.itineraryDayPlanHint,
                        style: const TextStyle(color: AppColors.ink3),
                      ),
                    )
                  else
                    ..._dayPlans.asMap().entries.map((entry) {
                      final index = entry.key;
                      final day = entry.value;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _DayPlanCard(
                          day: day,
                          date: DateUtils.addDaysToDate(
                            _dateRange!.start,
                            index,
                          ),
                          destinationNames: destinationNames,
                          canAddPlace: _destinationIds.any(
                            (id) => !day.destinationIds.contains(id),
                          ),
                          onNoteChanged: (value) {
                            _dayPlans[index] =
                                _dayPlans[index].copyWith(notes: value);
                          },
                          onAddPlace: () => _addPlaceToDay(index),
                          onRemovePlace: (placeIndex) =>
                              _removePlaceFromDay(index, placeIndex),
                          onMovePlace: (placeIndex, delta) =>
                              _movePlaceInDay(index, placeIndex, delta),
                        ),
                      );
                    }),
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
      setState(() {
        _dateRange = picked;
        _dayPlans = _buildDayPlans(
          picked.end.difference(picked.start).inDays + 1,
          existing: _dayPlans,
        );
      });
    }
  }

  List<ItineraryDay> _buildDayPlans(
    int dayCount, {
    List<ItineraryDay> existing = const [],
  }) {
    final plans = <ItineraryDay>[];
    for (var i = 1; i <= dayCount; i++) {
      final source = i <= existing.length ? existing[i - 1] : null;
      final destinationIds = source == null
          ? const <String>[]
          : source.destinationIds.where(_destinationIds.contains).toList();
      plans.add(
        source == null
            ? ItineraryDay(dayNumber: i)
            : source.copyWith(dayNumber: i, destinationIds: destinationIds),
      );
    }
    return plans;
  }

  Future<void> _addPlaceToDay(int dayIndex) async {
    final l10n = AppLocalizations.of(context);
    final languageCode = Localizations.localeOf(context).languageCode;
    final day = _dayPlans[dayIndex];
    final options = _destinationIds
        .where((id) => !day.destinationIds.contains(id))
        .toList();
    if (options.isEmpty) {
      return;
    }

    final selected = await showModalBottomSheet<String>(
      context: context,
      builder: (sheetContext) {
        return SafeArea(
          child: ListView(
            shrinkWrap: true,
            padding: const EdgeInsets.symmetric(vertical: 8),
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
                child: Text(
                  l10n.itinerarySelectPlace,
                  style: const TextStyle(
                    color: AppColors.ink,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              ...options.map((id) {
                final name = destinationNamesFor(id, languageCode);
                return ListTile(
                  leading: const Icon(
                    Icons.location_on_outlined,
                    color: AppColors.primary,
                  ),
                  title: Text(name),
                  onTap: () => Navigator.of(sheetContext).pop(id),
                );
              }),
            ],
          ),
        );
      },
    );

    if (selected == null || !mounted) {
      return;
    }
    final current = _dayPlans[dayIndex];
    if (current.destinationIds.contains(selected)) {
      return;
    }
    setState(() {
      _dayPlans[dayIndex] = current.copyWith(
        destinationIds: [...current.destinationIds, selected],
      );
    });
  }

  String destinationNamesFor(String id, String languageCode) {
    for (final destination in DestinationRepository.destinations) {
      if (destination.id == id) {
        return destination.getName(languageCode);
      }
    }
    return id;
  }

  void _removePlaceFromDay(int dayIndex, int placeIndex) {
    final day = _dayPlans[dayIndex];
    final destinationIds = [...day.destinationIds]..removeAt(placeIndex);
    setState(() {
      _dayPlans[dayIndex] = day.copyWith(destinationIds: destinationIds);
    });
  }

  void _movePlaceInDay(int dayIndex, int placeIndex, int delta) {
    final day = _dayPlans[dayIndex];
    final target = placeIndex + delta;
    if (target < 0 || target >= day.destinationIds.length) {
      return;
    }
    final destinationIds = [...day.destinationIds];
    final moved = destinationIds[placeIndex];
    destinationIds[placeIndex] = destinationIds[target];
    destinationIds[target] = moved;
    setState(() {
      _dayPlans[dayIndex] = day.copyWith(destinationIds: destinationIds);
    });
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
        days: _dayPlans,
        notes: _notesController.text.trim(),
      );
    } else {
      await provider.update(
        existing.copyWith(
          title: _titleController.text.trim(),
          startDate: range.start,
          endDate: range.end,
          destinationIds: _destinationIds.toList(),
          days: _dayPlans,
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

class _DayPlanCard extends StatelessWidget {
  final ItineraryDay day;
  final DateTime date;
  final Map<String, String> destinationNames;
  final bool canAddPlace;
  final ValueChanged<String> onNoteChanged;
  final VoidCallback onAddPlace;
  final ValueChanged<int> onRemovePlace;
  final void Function(int placeIndex, int delta) onMovePlace;

  const _DayPlanCard({
    required this.day,
    required this.date,
    required this.destinationNames,
    required this.canAddPlace,
    required this.onNoteChanged,
    required this.onAddPlace,
    required this.onRemovePlace,
    required this.onMovePlace,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final localizations = MaterialLocalizations.of(context);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  l10n.itineraryDayLabel(day.dayNumber),
                  style: const TextStyle(
                    color: AppColors.primary,
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  localizations.formatMediumDate(date),
                  style: const TextStyle(color: AppColors.ink3, fontSize: 13),
                ),
              ),
              TextButton.icon(
                onPressed: canAddPlace ? onAddPlace : null,
                icon: const Icon(Icons.add_location_alt_outlined, size: 18),
                label: Text(l10n.itineraryAddPlace),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.primary,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  minimumSize: const Size(0, 36),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          if (day.destinationIds.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Text(
                l10n.itineraryNoPlacesInDay,
                style: const TextStyle(color: AppColors.ink3, fontSize: 13),
              ),
            )
          else
            ...day.destinationIds.asMap().entries.map((entry) {
              final placeIndex = entry.key;
              final placeId = entry.value;
              final isFirst = placeIndex == 0;
              final isLast = placeIndex == day.destinationIds.length - 1;

              return Container(
                margin: const EdgeInsets.only(top: 6),
                padding: const EdgeInsets.fromLTRB(10, 2, 2, 2),
                decoration: BoxDecoration(
                  color: AppColors.pageBg,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.location_on_outlined,
                      size: 18,
                      color: AppColors.primary,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        destinationNames[placeId] ?? placeId,
                        style: const TextStyle(
                          color: AppColors.ink,
                          fontSize: 14,
                        ),
                      ),
                    ),
                    _DayPlaceIconButton(
                      icon: Icons.arrow_upward,
                      tooltip: l10n.itineraryMoveUp,
                      onPressed:
                          isFirst ? null : () => onMovePlace(placeIndex, -1),
                    ),
                    _DayPlaceIconButton(
                      icon: Icons.arrow_downward,
                      tooltip: l10n.itineraryMoveDown,
                      onPressed:
                          isLast ? null : () => onMovePlace(placeIndex, 1),
                    ),
                    _DayPlaceIconButton(
                      icon: Icons.close,
                      tooltip: l10n.itineraryRemovePlace,
                      onPressed: () => onRemovePlace(placeIndex),
                    ),
                  ],
                ),
              );
            }),
          const SizedBox(height: 8),
          TextFormField(
            key: Key('dayNotesField_${day.dayNumber}'),
            initialValue: day.notes,
            minLines: 1,
            maxLines: 3,
            onChanged: onNoteChanged,
            decoration: InputDecoration(
              isDense: true,
              hintText: l10n.itineraryDayNotesHint,
              hintStyle: const TextStyle(color: AppColors.ink3, fontSize: 13),
              filled: true,
              fillColor: AppColors.pageBg,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 10,
                vertical: 10,
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(color: AppColors.line),
              ),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(color: AppColors.line),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(6),
                borderSide: const BorderSide(
                  color: AppColors.primary,
                  width: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DayPlaceIconButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;

  const _DayPlaceIconButton({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(icon, size: 16),
      tooltip: tooltip,
      onPressed: onPressed,
      visualDensity: VisualDensity.compact,
      padding: EdgeInsets.zero,
      constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
      color: AppColors.ink3,
      disabledColor: AppColors.line,
    );
  }
}
