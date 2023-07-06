import { DateTime, Interval } from "luxon";

export const getDateDiffStr = (before: string, later: string) => {
  const startDT = DateTime.fromISO(before).toUTC();
  const endDT = DateTime.fromISO(later).toUTC();
  const diff = Interval.fromDateTimes(startDT, endDT);

  let interval = diff.length("years");
  let floored = Math.floor(interval);
  if (interval > 1) {
    if (floored === 1) {
      return `${floored} year ago`;
    }
    return `${floored} years ago`;
  }

  interval = diff.length("months");
  floored = Math.floor(interval);
  if (interval > 1) {
    floored = Math.floor(interval);
    if (floored === 1) {
      return `${floored} month ago`;
    }
    return `${floored} months ago`;
  }

  interval = diff.length("days");
  floored = Math.floor(interval);
  if (interval > 1) {
    if (floored === 1) {
      return `${floored} day ago`;
    }
    return `${floored} days ago`;
  }

  interval = diff.length("hours");
  floored = Math.floor(interval);
  if (interval > 1) {
    if (floored === 1) {
      return `${floored} hour ago`;
    }
    return `${floored} hours ago`;
  }

  interval = diff.length("minutes");
  floored = Math.floor(interval);
  if (interval > 1) {
    if (floored === 1) {
      return `${floored} minute ago`;
    }
    return `${floored} minutes ago`;
  }

  return "Just now";
};

export const getDateDiffWithSeconds = (start: Date, end: Date) => {
  const seconds = Math.floor((end - start) / 1000);
  if (seconds / 60 < 1) {
    return seconds + (seconds === 1 ? " second" : " seconds");
  }
  return getDateDiffStr(start, end);
};
