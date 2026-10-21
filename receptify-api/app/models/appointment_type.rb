class AppointmentType < ApplicationRecord
  belongs_to :client_workspace
  has_many :appointments, dependent: :restrict_with_error

  validates :name, presence: true
  validates :duration_minutes, numericality: { only_integer: true, greater_than: 0, less_than_or_equal_to: 480 }
end
