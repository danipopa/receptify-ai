module Api
  module V1
    class MockNumberRequestsController < BaseController
      COUNTRIES = {
        "GB" => { name: "United Kingdom", calling_code: "44", locale: "en-GB" },
        "US" => { name: "United States", calling_code: "1", locale: "en-US" },
        "FR" => { name: "France", calling_code: "33", locale: "fr-FR" },
        "IT" => { name: "Italy", calling_code: "39", locale: "it-IT" },
        "ES" => { name: "Spain", calling_code: "34", locale: "es-ES" },
        "RO" => { name: "Romania", calling_code: "40", locale: "ro-RO" }
      }.freeze

      def create
        workspace = current_tenant.client_workspaces.find(params[:client_workspace_id])
        country_code = params.require(:country_code).to_s.upcase
        country = COUNTRIES[country_code]
        return render json: { error: "Unsupported country" }, status: :unprocessable_entity unless country

        number = generate_number(country.fetch(:calling_code))
        request = workspace.mock_number_requests.create!(
          country_code: country_code,
          country_name: country.fetch(:name),
          locale: country.fetch(:locale),
          number: number
        )
        workspace.update!(locale: country.fetch(:locale))

        render json: {
          number_request: request.as_json(only: %i[id country_code country_name locale number simulated created_at]),
          notice: "Simulator number. It can be dialed through a Linphone account registered to this FreeSWITCH, but is not reachable from the public phone network."
        }, status: :created
      end

      private

      def generate_number(calling_code)
        10.times do
          number = "+#{calling_code}000000#{SecureRandom.random_number(10_000).to_s.rjust(4, '0')}"
          return number unless MockNumberRequest.exists?(number: number) || Did.exists?(number: number)
        end
        raise ActiveRecord::RecordNotUnique, "Could not allocate a unique simulator number"
      end
    end
  end
end
