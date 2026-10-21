class MockNumberRequest < ApplicationRecord
  belongs_to :client_workspace

  validates :country_code, :country_name, :locale, :number, presence: true
  validates :number, uniqueness: true
  validates :simulated, inclusion: { in: [true] }
end
