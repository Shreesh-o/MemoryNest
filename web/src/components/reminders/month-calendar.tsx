"use client";

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  BellIcon,
  CalendarIcon,
  CheckIcon,
  ClockIcon,
  XIcon,
  RotateCwIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { calendarItems, type CalendarItem } from "@/lib/api";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

interface MonthCalendarProps {
  onConfirmEvent: (eventId: number) => void;
  onDiscardEvent: (eventId: number) => void;
  onCancelReminder: (reminderId: number) => void;
  onSendReminderNow: (reminderId: number) => void;
  onSyncReminder?: (reminderId: number) => void;
  isSyncingReminderId?: number | null;
}

export function CalendarSyncBadge({
  status,
  onRetry,
  isRetrying,
}: {
  status?: string | null;
  onRetry?: () => void;
  isRetrying?: boolean;
}) {
  if (!status || status === "not_synced") return null;

  if (status === "synced") {
    return (
      <Badge
        variant="success"
        className="text-[10px] py-0 px-1.5 font-normal"
      >
        Synced
      </Badge>
    );
  }

  if (status === "failed") {
    return (
      <span className="inline-flex items-center gap-1">
        <Badge variant="destructive" className="text-[10px] py-0 px-1.5 font-normal">
          Sync failed
        </Badge>
        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            className="h-5 px-1.5 text-[10px] text-destructive hover:bg-destructive/10 cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              onRetry();
            }}
            disabled={isRetrying}
          >
            {isRetrying ? (
              <RotateCwIcon className="size-2.5 animate-spin" />
            ) : (
              "Retry"
            )}
          </Button>
        )}
      </span>
    );
  }

  if (status === "not_connected") {
    return (
      <Badge
        variant="outline"
        className="text-muted-foreground text-[10px] py-0 px-1.5 font-normal"
      >
        Not connected
      </Badge>
    );
  }

  return null;
}

function formatLocalDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function MonthCalendar({
  onConfirmEvent,
  onDiscardEvent,
  onCancelReminder,
  onSendReminderNow,
  onSyncReminder,
  isSyncingReminderId,
}: MonthCalendarProps) {
  const [isOpen, setIsOpen] = useState(true);

  const [currentYear, setCurrentYear] = useState(() => new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(() => new Date().getMonth());
  const [selectedDate, setSelectedDate] = useState<string>(() => formatLocalDate(new Date()));
  const [dialogOpen, setDialogOpen] = useState(false);

  // Calculate calendar grid days (Monday-first)
  const calendarDays = useMemo(() => {
    const firstDayOfMonth = new Date(currentYear, currentMonth, 1);
    const lastDayOfMonth = new Date(currentYear, currentMonth + 1, 0);

    const startDayOfWeek = (firstDayOfMonth.getDay() + 6) % 7;
    const totalDaysInMonth = lastDayOfMonth.getDate();

    const days: {
      date: Date;
      dateStr: string;
      dayNumber: number;
      isCurrentMonth: boolean;
      isToday: boolean;
    }[] = [];

    const todayStr = formatLocalDate(new Date());

    // Preceding month padding
    const prevMonthLastDay = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const d = new Date(currentYear, currentMonth - 1, prevMonthLastDay - i);
      const dateStr = formatLocalDate(d);
      days.push({
        date: d,
        dateStr,
        dayNumber: prevMonthLastDay - i,
        isCurrentMonth: false,
        isToday: dateStr === todayStr,
      });
    }

    // Current month days
    for (let i = 1; i <= totalDaysInMonth; i++) {
      const d = new Date(currentYear, currentMonth, i);
      const dateStr = formatLocalDate(d);
      days.push({
        date: d,
        dateStr,
        dayNumber: i,
        isCurrentMonth: true,
        isToday: dateStr === todayStr,
      });
    }

    // Next month padding
    const remainingCells = (7 - (days.length % 7)) % 7;
    for (let i = 1; i <= remainingCells; i++) {
      const d = new Date(currentYear, currentMonth + 1, i);
      const dateStr = formatLocalDate(d);
      days.push({
        date: d,
        dateStr,
        dayNumber: i,
        isCurrentMonth: false,
        isToday: dateStr === todayStr,
      });
    }

    return days;
  }, [currentYear, currentMonth]);

  const startDateStr = calendarDays[0]?.dateStr || "";
  const endDateStr = calendarDays[calendarDays.length - 1]?.dateStr || "";

  // Fetch items for the visible range
  const { data: items = [] } = useQuery<CalendarItem[]>({
    queryKey: ["calendar-items", startDateStr, endDateStr],
    queryFn: async () => {
      if (!startDateStr || !endDateStr) return [];
      const res = await calendarItems(startDateStr, endDateStr);
      if (!res.ok) {
        throw new Error(res.error?.detail || "Failed to load calendar items");
      }
      return res.data;
    },
    enabled: Boolean(startDateStr && endDateStr),
  });

  // Group items by date string (YYYY-MM-DD)
  const itemsByDate = useMemo(() => {
    const map: Record<string, CalendarItem[]> = {};
    for (const item of items) {
      const dateKey = item.date.slice(0, 10);
      if (!map[dateKey]) {
        map[dateKey] = [];
      }
      map[dateKey].push(item);
    }
    return map;
  }, [items]);

  const goToPrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const goToNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
    }
  };

  const goToToday = () => {
    const today = new Date();
    setCurrentYear(today.getFullYear());
    setCurrentMonth(today.getMonth());
    const todayStr = formatLocalDate(today);
    setSelectedDate(todayStr);
  };

  const monthLabel = useMemo(() => {
    const d = new Date(currentYear, currentMonth, 1);
    return new Intl.DateTimeFormat("en-US", {
      month: "long",
      year: "numeric",
      timeZone: "Asia/Kolkata",
    }).format(d);
  }, [currentYear, currentMonth]);

  const handleDayClick = (dateStr: string) => {
    setSelectedDate(dateStr);
    setDialogOpen(true);
  };

  const selectedDayItems = itemsByDate[selectedDate] || [];

  return (
    <Card className="mb-6 border border-border/80 shadow-xs">
      <CardHeader
        className="py-3 px-4 flex flex-row items-center justify-between cursor-pointer select-none bg-muted/20 hover:bg-muted/30 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2.5">
          <CalendarIcon className="size-4.5 text-primary" />
          <CardTitle className="text-base font-semibold tracking-tight">Calendar View</CardTitle>
          <span className="text-xs text-muted-foreground font-medium">
            ({monthLabel})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="size-7 p-0 cursor-pointer"
            onClick={(e) => {
              e.stopPropagation();
              setIsOpen(!isOpen);
            }}
            aria-label={isOpen ? "Collapse calendar" : "Expand calendar"}
          >
            {isOpen ? <ChevronUpIcon className="size-4" /> : <ChevronDownIcon className="size-4" />}
          </Button>
        </div>
      </CardHeader>

      {isOpen && (
        <CardContent className="pt-4 px-3 sm:px-4 pb-4 space-y-4">
          {/* Calendar Header Controls */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-1">
            <h3 className="font-heading text-base sm:text-lg font-bold tracking-tight text-foreground">{monthLabel}</h3>
            <div className="flex items-center gap-1.5">
              <Button
                variant="outline"
                size="sm"
                className="size-8 p-0 cursor-pointer"
                onClick={goToPrevMonth}
                aria-label="Previous month"
              >
                <ChevronLeftIcon className="size-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-8 px-3 text-xs font-medium cursor-pointer"
                onClick={goToToday}
              >
                Today
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="size-8 p-0 cursor-pointer"
                onClick={goToNextMonth}
                aria-label="Next month"
              >
                <ChevronRightIcon className="size-4" />
              </Button>
            </div>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground py-1">
            {WEEKDAYS.map((day) => (
              <div key={day} className="py-0.5">
                {day}
              </div>
            ))}
          </div>

          {/* Month grid */}
          <div className="grid grid-cols-7 gap-1 bg-border/40 p-1 rounded-xl border border-border/60">
            {calendarDays.map((day) => {
              const dayItems = itemsByDate[day.dateStr] || [];
              const visibleItems = dayItems.slice(0, 3);
              const extraCount = dayItems.length - 3;
              const isSelected = selectedDate === day.dateStr;

              return (
                <div
                  key={day.dateStr}
                  onClick={() => handleDayClick(day.dateStr)}
                  role="button"
                  tabIndex={0}
                  className={`min-h-[64px] sm:min-h-[96px] p-1 sm:p-1.5 rounded-lg flex flex-col justify-start transition-all cursor-pointer select-none bg-card text-card-foreground hover:bg-accent/40 ${
                    !day.isCurrentMonth ? "opacity-35" : ""
                  } ${
                    isSelected ? "ring-2 ring-primary ring-offset-1" : ""
                  } ${
                    day.isToday ? "border border-primary/50 bg-primary/[0.04]" : "border border-border/30"
                  }`}
                >
                  {/* Day header number */}
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-xs inline-flex items-center justify-center rounded-full size-5.5 ${
                        day.isToday
                          ? "bg-primary text-primary-foreground font-bold shadow-xs"
                          : "font-medium"
                      }`}
                    >
                      {day.dayNumber}
                    </span>

                    {/* Mobile item count badge */}
                    {dayItems.length > 0 && (
                      <span className="sm:hidden text-[9px] font-semibold text-muted-foreground">
                        {dayItems.length}
                      </span>
                    )}
                  </div>

                  {/* Desktop Item Pills */}
                  <div className="hidden sm:flex flex-col gap-1 w-full overflow-hidden">
                    {visibleItems.map((item) => {
                      if (item.kind === "reminder") {
                        return (
                          <div
                            key={`rem-${item.id}`}
                            title={item.title}
                            className="bg-info/10 text-info border border-info/30 text-[10px] font-medium px-1.5 py-0.5 rounded truncate flex items-center gap-1 shadow-2xs"
                          >
                            <BellIcon className="size-2.5 shrink-0" />
                            <span className="truncate">{item.title}</span>
                          </div>
                        );
                      }

                      // Event: confirmed = solid, pending = outlined
                      if (item.status === "confirmed") {
                        return (
                          <div
                            key={`ev-${item.id}`}
                            title={item.title}
                            className="bg-primary text-primary-foreground text-[10px] font-medium px-1.5 py-0.5 rounded truncate flex items-center gap-1 shadow-2xs"
                          >
                            <CheckIcon className="size-2.5 shrink-0" />
                            <span className="truncate">{item.title}</span>
                          </div>
                        );
                      }

                      // Pending event: outlined
                      return (
                        <div
                          key={`ev-${item.id}`}
                          title={item.title}
                          className="border border-warning/50 text-warning-foreground bg-warning/15 text-[10px] font-medium px-1.5 py-0.5 rounded truncate flex items-center gap-1 shadow-2xs"
                        >
                          <ClockIcon className="size-2.5 shrink-0" />
                          <span className="truncate">{item.title}</span>
                        </div>
                      );
                    })}

                    {extraCount > 0 && (
                      <span className="text-[9px] font-medium text-muted-foreground pl-0.5">
                        +{extraCount} more
                      </span>
                    )}
                  </div>

                  {/* Mobile Compact Dots */}
                  <div className="sm:hidden flex flex-wrap gap-1 mt-auto pt-0.5 justify-center">
                    {dayItems.slice(0, 4).map((item, idx) => (
                      <span
                        key={idx}
                        className={`size-1.5 rounded-full ${
                          item.kind === "reminder"
                            ? "bg-info"
                            : item.status === "confirmed"
                            ? "bg-primary"
                            : "bg-warning"
                        }`}
                      />
                    ))}
                    {dayItems.length > 4 && (
                      <span className="size-1.5 rounded-full bg-muted-foreground" />
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Mobile view: list of selected day's items below calendar */}
          <div className="block sm:hidden border border-border/80 rounded-xl p-3 bg-muted/20 space-y-2 mt-3">
            <div className="flex items-center justify-between text-xs font-semibold">
              <span>Items on {selectedDate}:</span>
              <span className="text-muted-foreground">({selectedDayItems.length})</span>
            </div>
            {selectedDayItems.length === 0 ? (
              <p className="text-xs text-muted-foreground py-1">No items on this day.</p>
            ) : (
              <div className="space-y-1.5">
                {selectedDayItems.map((item) => (
                  <div
                    key={`${item.kind}-${item.id}`}
                    className="flex items-center justify-between p-2.5 rounded-lg border border-border/80 bg-card text-xs gap-2"
                  >
                    <div className="flex items-center gap-1.5 truncate">
                      {item.kind === "reminder" ? (
                        <BellIcon className="size-3.5 text-info shrink-0" />
                      ) : item.status === "confirmed" ? (
                        <CheckIcon className="size-3.5 text-primary shrink-0" />
                      ) : (
                        <ClockIcon className="size-3.5 text-warning shrink-0" />
                      )}
                      <span className="truncate font-medium">{item.title}</span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Badge variant={item.status === "confirmed" ? "default" : "outline"} className="text-[10px] capitalize shrink-0">
                        {item.status}
                      </Badge>
                      {item.sync_status && (
                        <CalendarSyncBadge
                          status={item.sync_status}
                          onRetry={item.kind === "reminder" && onSyncReminder ? () => onSyncReminder(item.id) : undefined}
                          isRetrying={isSyncingReminderId === item.id}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      )}

      {/* Day Details Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <CalendarIcon className="size-4.5 text-primary" />
              Events & Reminders
            </DialogTitle>
            <DialogDescription>
              {selectedDate
                ? new Intl.DateTimeFormat("en-IN", {
                    timeZone: "Asia/Kolkata",
                    dateStyle: "full",
                  }).format(new Date(`${selectedDate}T00:00:00`))
                : ""}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 mt-2 max-h-[60vh] overflow-y-auto pr-1">
            {selectedDayItems.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">
                No events or reminders scheduled for this date.
              </p>
            ) : (
              selectedDayItems.map((item) => (
                <div
                  key={`${item.kind}-${item.id}`}
                  className="p-3.5 rounded-xl border border-border/80 bg-card space-y-2 shadow-2xs"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                        {item.kind === "reminder" ? (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-info">
                            <BellIcon className="size-3.5" /> Reminder
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
                            <CalendarIcon className="size-3.5" /> Event
                          </span>
                        )}
                        <Badge
                          variant={item.status === "confirmed" || item.status === "scheduled" ? "default" : "outline"}
                          className="capitalize text-[10px] py-0 px-1.5"
                        >
                          {item.status}
                        </Badge>
                        {item.sync_status && (
                          <CalendarSyncBadge
                            status={item.sync_status}
                            onRetry={item.kind === "reminder" && onSyncReminder ? () => onSyncReminder(item.id) : undefined}
                            isRetrying={isSyncingReminderId === item.id}
                          />
                        )}
                      </div>
                      <p className="text-sm font-medium leading-snug">{item.title}</p>
                      <p className="text-xs text-muted-foreground mt-1 font-mono">
                        {item.all_day ? "All-day" : item.date}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex justify-end gap-1.5 pt-2 border-t border-border/60">
                    {item.kind === "event" && item.status === "pending" && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7.5 text-xs gap-1 cursor-pointer"
                          onClick={() => {
                            setDialogOpen(false);
                            onConfirmEvent(item.id);
                          }}
                        >
                          <CheckIcon className="size-3" /> Confirm
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
                          onClick={() => {
                            setDialogOpen(false);
                            onDiscardEvent(item.id);
                          }}
                        >
                          <XIcon className="size-3 mr-1" /> Discard
                        </Button>
                      </>
                    )}

                    {item.kind === "reminder" && item.status === "scheduled" && (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7.5 text-xs gap-1 cursor-pointer"
                          onClick={() => {
                            setDialogOpen(false);
                            onSendReminderNow(item.id);
                          }}
                        >
                          <ClockIcon className="size-3" /> Send now
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7.5 text-xs text-destructive hover:bg-destructive/10 cursor-pointer"
                          onClick={() => {
                            setDialogOpen(false);
                            onCancelReminder(item.id);
                          }}
                        >
                          <XIcon className="size-3 mr-1" /> Cancel
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
