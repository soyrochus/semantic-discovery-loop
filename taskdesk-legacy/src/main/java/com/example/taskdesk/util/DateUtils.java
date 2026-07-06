package com.example.taskdesk.util;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;

public final class DateUtils {
    private static final String DATE_PATTERN = "yyyy-MM-dd";
    private static final String DATE_TIME_PATTERN = "yyyy-MM-dd'T'HH:mm:ss";

    private DateUtils() {
    }

    public static Date parseDate(String value) {
        if (value == null || value.trim().length() == 0) {
            return null;
        }
        try {
            SimpleDateFormat format = new SimpleDateFormat(DATE_PATTERN);
            format.setLenient(false);
            return format.parse(value.trim());
        } catch (ParseException e) {
            throw new IllegalArgumentException("Invalid date: " + value, e);
        }
    }

    public static Date parseDateTime(String value) {
        if (value == null || value.trim().length() == 0) {
            return null;
        }
        try {
            SimpleDateFormat format = new SimpleDateFormat(DATE_TIME_PATTERN);
            format.setLenient(false);
            return format.parse(value.trim());
        } catch (ParseException e) {
            throw new IllegalArgumentException("Invalid date/time: " + value, e);
        }
    }

    public static String formatDate(Date value) {
        if (value == null) {
            return "";
        }
        return new SimpleDateFormat(DATE_PATTERN).format(value);
    }

    public static String formatDateTime(Date value) {
        if (value == null) {
            return null;
        }
        return new SimpleDateFormat(DATE_TIME_PATTERN).format(value);
    }

    public static String nowDateTime() {
        return formatDateTime(new Date());
    }
}
