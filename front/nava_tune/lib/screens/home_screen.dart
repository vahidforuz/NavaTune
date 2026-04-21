import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.onNavigate});

  final ValueChanged<int> onNavigate;

  @override
  Widget build(BuildContext context) {
    const quickActions = [
      _QuickActionData(
        title: 'Start Tuning',
        subtitle: 'Open the tuner and begin listening right away.',
        icon: Icons.tune_rounded,
        color: Color(0xFF2A6F97),
        tabIndex: 1,
      ),
      _QuickActionData(
        title: 'Audio Stream',
        subtitle: 'Check incoming sound and monitor live input.',
        icon: Icons.graphic_eq_rounded,
        color: Color(0xFF3A7D44),
        tabIndex: 2,
      ),
      _QuickActionData(
        title: 'Saved Melodies',
        subtitle: 'Review the ideas and melodies you kept.',
        icon: Icons.library_music_rounded,
        color: Color(0xFFB26E3B),
        tabIndex: 3,
      ),
      _QuickActionData(
        title: 'Settings',
        subtitle: 'Adjust microphone access and app preferences.',
        icon: Icons.settings_rounded,
        color: Color(0xFF6C5B7B),
        tabIndex: 4,
      ),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF6F1E9),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(28),
                  gradient: const LinearGradient(
                    colors: [Color(0xFF12343B), Color(0xFF2D5F5D)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: const [
                    BoxShadow(
                      color: Color(0x1A000000),
                      blurRadius: 20,
                      offset: Offset(0, 10),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0x26FFFFFF),
                        borderRadius: BorderRadius.circular(999),
                      ),
                      child: const Text(
                        'NavaTune',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.4,
                        ),
                      ),
                    ),
                    const SizedBox(height: 18),
                    const Text(
                      'Tune faster.\nCapture ideas before they fade.',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 30,
                        fontWeight: FontWeight.w700,
                        height: 1.15,
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Use the tuner for pitch, stream live audio, and keep your best melodies in one place.',
                      style: TextStyle(
                        color: Color(0xFFE2EFEA),
                        fontSize: 15,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 22),
                    FilledButton.icon(
                      onPressed: () => onNavigate(1),
                      style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFFF2C14E),
                        foregroundColor: const Color(0xFF1F1F1F),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 14,
                        ),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                      icon: const Icon(Icons.play_arrow_rounded),
                      label: const Text('Start Tuning'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'Quick Actions',
                style: TextStyle(
                  color: Color(0xFF172121),
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 12),
              ...quickActions.map(
                (action) => Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: _QuickActionCard(
                    data: action,
                    onTap: () => onNavigate(action.tabIndex),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: const [
                  Expanded(
                    child: _StatusCard(
                      title: 'Mic Status',
                      value: 'Check',
                      note: 'Open Settings to confirm permission access.',
                    ),
                  ),
                  SizedBox(width: 12),
                  Expanded(
                    child: _StatusCard(
                      title: 'Last Session',
                      value: 'None',
                      note: 'Your recent tuning activity can appear here later.',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const _TipCard(),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuickActionCard extends StatelessWidget {
  const _QuickActionCard({required this.data, required this.onTap});

  final _QuickActionData data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(22),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(22),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: data.color.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(data.icon, color: data.color),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      data.title,
                      style: const TextStyle(
                        color: Color(0xFF172121),
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      data.subtitle,
                      style: const TextStyle(
                        color: Color(0xFF5B6666),
                        fontSize: 14,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              const Icon(
                Icons.arrow_forward_ios_rounded,
                size: 16,
                color: Color(0xFF7A8585),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({
    required this.title,
    required this.value,
    required this.note,
  });

  final String title;
  final String value;
  final String note;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFFE7ECEB),
        borderRadius: BorderRadius.circular(22),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF435252),
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: const TextStyle(
              color: Color(0xFF172121),
              fontSize: 22,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            note,
            style: const TextStyle(
              color: Color(0xFF5B6666),
              fontSize: 13,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }
}

class _TipCard extends StatelessWidget {
  const _TipCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFCF5),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: const Color(0xFFE7D8B1)),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Good First Step',
            style: TextStyle(
              color: Color(0xFF7B5A16),
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.3,
            ),
          ),
          SizedBox(height: 10),
          Text(
            'Open the tuner in a quiet room, test microphone access, and save one short melody so the rest of the app has data to build on.',
            style: TextStyle(
              color: Color(0xFF5C4A24),
              fontSize: 14,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickActionData {
  const _QuickActionData({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.tabIndex,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final int tabIndex;
}
