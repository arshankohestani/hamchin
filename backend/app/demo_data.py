from .models import ConflictGroup, DemandGroup, OfferingInput, RoomInput, SessionInput, TimeSlot


_DAYS = [
    ("sat", "شنبه"),
    ("sun", "یکشنبه"),
    ("mon", "دوشنبه"),
    ("tue", "سه‌شنبه"),
    ("wed", "چهارشنبه"),
    ("thu", "پنجشنبه"),
]
_TIMES = [
    ("08", "08:00", "10:00", "۸", "۱۰"),
    ("10", "10:00", "12:00", "۱۰", "۱۲"),
    ("12", "12:00", "14:00", "۱۲", "۱۴"),
    ("14", "14:00", "16:00", "۱۴", "۱۶"),
    ("16", "16:00", "18:00", "۱۶", "۱۸"),
]

SLOTS = [
    TimeSlot(
        id=f"{day_id}-{time_id}",
        day=day_name,
        start=start,
        end=end,
        label=f"{day_name}، {start_fa} تا {end_fa}",
    )
    for day_id, day_name in _DAYS
    for time_id, start, end, start_fa, end_fa in _TIMES
]


ROOMS = [
    RoomInput(id="r201", name="کلاس ۲۰۱", capacity=45),
    RoomInput(id="r202", name="کلاس ۲۰۲", capacity=40),
    RoomInput(id="r203", name="کلاس ۲۰۳", capacity=36),
    RoomInput(id="r204", name="کلاس ۲۰۴", capacity=32),
    RoomInput(id="lab1", name="آزمایشگاه شبکه", capacity=28, kind="lab"),
    RoomInput(id="lab2", name="آزمایشگاه سخت‌افزار", capacity=24, kind="lab"),
]


OFFERINGS = [
    OfferingInput(id="diff-g1", course_id="diff", code="SCI-103", title="معادلات دیفرانسیل", instructor="دکتر رهنما", preferred_semester=3, group_number=1, weekly_sessions=2, sessions=[SessionInput(meeting_number=1, week_pattern="every"), SessionInput(meeting_number=2, week_pattern="odd", fixed_slot_id="tue-08")], capacity=38, available_slot_ids=["sat-08", "sun-14", "mon-10", "tue-08"], flexibility=5),
    OfferingInput(id="diff-g2", course_id="diff", code="SCI-103", title="معادلات دیفرانسیل", instructor="دکتر رهنما", preferred_semester=3, group_number=2, weekly_sessions=1, capacity=38, available_slot_ids=["sat-08", "sun-14", "mon-10", "tue-08"], flexibility=5),
    OfferingInput(id="data-g1", course_id="data", code="CSE-110", title="ساختمان داده‌ها و الگوریتم‌ها", instructor="دکتر کاظمی", preferred_semester=3, group_number=1, weekly_sessions=1, capacity=34, available_slot_ids=["sat-10", "sun-08", "mon-14", "tue-10"], flexibility=5),
    OfferingInput(id="data-g2", course_id="data", code="CSE-110", title="ساختمان داده‌ها و الگوریتم‌ها", instructor="دکتر کاظمی", preferred_semester=3, group_number=2, weekly_sessions=1, capacity=34, available_slot_ids=["sat-10", "sun-08", "mon-14", "tue-10"], flexibility=5),
    OfferingInput(id="soft-g1", course_id="soft", code="CSE-150", title="مهارت‌های نرم شغلی", instructor="دکتر نادری", preferred_semester=3, group_number=1, weekly_sessions=1, capacity=40, available_slot_ids=["sat-14", "sun-10", "mon-08", "tue-14"], flexibility=5, kind="skill"),
    OfferingInput(id="soft-g2", course_id="soft", code="CSE-150", title="مهارت‌های نرم شغلی", instructor="دکتر نادری", preferred_semester=3, group_number=2, weekly_sessions=1, week_pattern="even", capacity=40, available_slot_ids=["sat-14", "sun-10", "mon-08", "tue-14"], flexibility=5, kind="skill"),
    OfferingInput(id="ai-g1", course_id="ai", code="CSE-116", title="هوش مصنوعی", instructor="دکتر پارسا", preferred_semester=5, group_number=1, weekly_sessions=1, capacity=36, available_slot_ids=["sat-08", "sun-10", "mon-14"], flexibility=4),
    OfferingInput(id="os-g1", course_id="os", code="CSE-118", title="سیستم‌های عامل", instructor="دکتر سهرابی", preferred_semester=5, group_number=1, weekly_sessions=1, capacity=32, available_slot_ids=["sat-10", "sun-14", "mon-08", "tue-10"], flexibility=5),
    OfferingInput(id="os-g2", course_id="os", code="CSE-118", title="سیستم‌های عامل", instructor="دکتر سهرابی", preferred_semester=5, group_number=2, weekly_sessions=1, capacity=32, available_slot_ids=["sat-10", "sun-14", "mon-08", "tue-10"], flexibility=5),
    OfferingInput(id="research-g1", course_id="research", code="CSE-120", title="روش پژوهش و ارائه", instructor="دکتر رهنما", preferred_semester=5, group_number=1, weekly_sessions=1, capacity=42, available_slot_ids=["sat-08", "sun-14", "mon-10", "tue-08"], flexibility=3),
    OfferingInput(id="network-g1", course_id="network", code="CSE-122", title="شبکه‌های کامپیوتری", instructor="دکتر کیانی", preferred_semester=6, group_number=1, weekly_sessions=1, capacity=35, available_slot_ids=["sat-14", "sun-08", "mon-10", "tue-14"], flexibility=5),
    OfferingInput(id="network-g2", course_id="network", code="CSE-122", title="شبکه‌های کامپیوتری", instructor="دکتر کیانی", preferred_semester=6, group_number=2, weekly_sessions=1, capacity=35, available_slot_ids=["sat-14", "sun-08", "mon-10", "tue-14"], flexibility=5),
    OfferingInput(id="analysis-g1", course_id="analysis", code="CSE-121", title="تحلیل و طراحی نرم‌افزار", instructor="دکتر نادری", preferred_semester=6, group_number=1, weekly_sessions=1, capacity=38, available_slot_ids=["sat-14", "sun-10", "mon-08", "tue-14"], flexibility=4),
    OfferingInput(id="security-g1", course_id="security", code="CSE-124", title="امنیت سیستم‌های کامپیوتری", instructor="دکتر پارسا", preferred_semester=7, group_number=1, weekly_sessions=1, capacity=34, available_slot_ids=["sat-08", "sun-10", "mon-14"], flexibility=3),
]

# در فرم اولیه هیچ ساعتی از طرف مدیرگروه فرض نمی‌شود؛ هر استاد باید صریحاً تنظیم شود.
for _offering in OFFERINGS:
    _offering.available_slot_ids = []
    for _session in _offering.sessions:
        _session.fixed_slot_id = None


# این تعدادها برآورد نسخه نمایشی‌اند و پس از دریافت آمار آموزشی با داده واقعی جایگزین می‌شوند.
DEMAND_GROUPS = [
    DemandGroup(id="semester-3", label="دانشجویان چارت ترم ۳", student_count=62, course_ids=["diff", "data", "soft"], weight=5),
    DemandGroup(id="semester-5", label="دانشجویان عادی چارت ترم ۵", student_count=36, course_ids=["ai", "os", "research"], weight=5),
    DemandGroup(id="semester-6", label="دانشجویان چارت ترم ۶", student_count=48, course_ids=["network", "analysis"], weight=5),
    DemandGroup(id="backlog-diff-5", label="ترم ۵ با معادلات عقب‌افتاده", student_count=18, course_ids=["diff", "ai", "os", "research"], weight=7),
    DemandGroup(id="soft-skills-7", label="ترم ۷ متقاضی مهارت‌های نرم", student_count=14, course_ids=["soft", "security", "network"], weight=7),
]


CONFLICT_GROUPS = [
    ConflictGroup(id="entry-1403", label="چارت اصلی ترم سوم", entry_year="ورودی ۱۴۰۳", course_ids=["diff", "data", "soft"]),
    ConflictGroup(id="entry-1401-backlog", label="ترم پنجم همراه معادلات عقب‌افتاده", entry_year="ورودی ۱۴۰۱", course_ids=["diff", "ai", "os", "research"]),
    ConflictGroup(id="cross-semester", label="سبد انتخابی بین‌ترمی", entry_year="چند ورودی", course_ids=["soft", "network", "security"]),
]

