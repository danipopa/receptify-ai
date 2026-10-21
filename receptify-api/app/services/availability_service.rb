class AvailabilityService
  MAX_RANGE_DAYS = 62
  MAX_RESULTS = 100

  def initialize(client_workspace:, appointment_type:)
    @client_workspace = client_workspace
    @appointment_type = appointment_type
    @zone = Time.find_zone!(client_workspace.timezone)
  end

  def slots(from:, to:, limit: 20)
    raise ArgumentError, "date range is invalid" if to < from
    raise ArgumentError, "date range cannot exceed #{MAX_RANGE_DAYS} days" if (to - from).to_i > MAX_RANGE_DAYS

    result_limit = [[limit.to_i, 1].max, MAX_RESULTS].min
    slots = []
    (from..to).each do |date|
      day_slots(date, result_limit - slots.length).each { |slot| slots << slot }
      break if slots.length >= result_limit
    end
    slots
  end

  def available?(starts_at)
    local_start = starts_at.in_time_zone(@zone)
    slots(from: local_start.to_date, to: local_start.to_date, limit: MAX_RESULTS).any? do |slot|
      Time.iso8601(slot.fetch(:starts_at)).utc == starts_at.utc
    end
  end

  private

  def day_slots(date, remaining)
    exceptions = @client_workspace.availability_exceptions.where(date: date).to_a
    return [] if exceptions.any?(&:all_day?)

    day_start = @zone.local(date.year, date.month, date.day)
    day_end = day_start + 1.day
    booked = @client_workspace.appointments
                              .where(status: "confirmed")
                              .where("starts_at < ? AND ends_at > ?", day_end.utc, day_start.utc)
                              .to_a
    duration = @appointment_type.duration_minutes.minutes
    result = []

    @client_workspace.availability_rules.where(day_of_week: date.wday).order(:start_time).each do |rule|
      cursor = local_time(date, rule.start_time)
      finish = local_time(date, rule.end_time)
      while cursor + duration <= finish
        slot_end = cursor + duration
        unless cursor <= Time.current || blocked?(cursor, slot_end, exceptions) ||
               booked.any? { |appointment| appointment.starts_at < slot_end && appointment.ends_at > cursor }
          result << {
            starts_at: cursor.utc.iso8601,
            ends_at: slot_end.utc.iso8601,
            local_time: cursor.strftime("%A %d %B %Y at %H:%M %Z")
          }
          return result if result.length >= remaining
        end
        cursor += duration
      end
    end
    result
  end

  def blocked?(slot_start, slot_end, exceptions)
    exceptions.any? do |exception|
      next false if exception.all_day?

      block_start = local_time(exception.date, exception.start_time)
      block_end = local_time(exception.date, exception.end_time)
      slot_start < block_end && slot_end > block_start
    end
  end

  def local_time(date, value)
    hour, minute = value.split(":").map(&:to_i)
    @zone.local(date.year, date.month, date.day, hour, minute)
  end
end
