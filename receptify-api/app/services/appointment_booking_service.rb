class AppointmentBookingService
  class SlotUnavailable < StandardError; end

  def initialize(client_workspace:, appointment_type:)
    @client_workspace = client_workspace
    @appointment_type = appointment_type
  end

  def call(caller_name:, callback_number:, starts_at:, purpose: nil)
    parsed_start = Time.iso8601(starts_at).utc

    @client_workspace.with_lock do
      available = AvailabilityService.new(
        client_workspace: @client_workspace,
        appointment_type: @appointment_type
      ).available?(parsed_start)
      raise SlotUnavailable, "That appointment slot is no longer available" unless available

      @client_workspace.appointments.create!(
        appointment_type: @appointment_type,
        caller_name: caller_name,
        callback_number: callback_number,
        purpose: purpose,
        starts_at: parsed_start,
        ends_at: parsed_start + @appointment_type.duration_minutes.minutes,
        status: "confirmed"
      )
    end
  end
end
