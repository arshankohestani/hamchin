"use client";

import {
  BookOpenText,
  CalendarDays,
  ChartNoAxesCombined,
  ChevronLeft,
  GraduationCap,
  LayoutDashboard,
  Settings2,
  Sparkles,
  UsersRound,
} from "lucide-react";

const items = [
  { label: "نمای کلی", icon: LayoutDashboard, active: true },
  { label: "ارائه دروس", icon: BookOpenText },
  { label: "اساتید", icon: UsersRound },
  { label: "زمان‌بندی هوشمند", icon: Sparkles, badge: "AI" },
  { label: "تقویم هفتگی", icon: CalendarDays },
  { label: "گزارش‌ها", icon: ChartNoAxesCombined },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark"><GraduationCap size={25} /></div>
        <div><strong>هم‌چین</strong><span>دستیار مدیرگروه</span></div>
      </div>

      <nav className="side-nav" aria-label="منوی اصلی">
        <span className="nav-caption">مدیریت برنامه</span>
        {items.map(({ label, icon: Icon, active, badge }) => (
          <button className={`nav-item ${active ? "active" : ""}`} key={label} type="button">
            <Icon size={19} />
            <span>{label}</span>
            {badge && <small>{badge}</small>}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button className="nav-item" type="button"><Settings2 size={19} /><span>تنظیمات</span></button>
        <div className="profile-mini">
          <div className="avatar">م</div>
          <div><strong>مدیر گروه</strong><span>مهندسی کامپیوتر</span></div>
          <ChevronLeft size={17} />
        </div>
      </div>
    </aside>
  );
}

