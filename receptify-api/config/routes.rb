Rails.application.routes.draw do
  namespace :api do
    namespace :v1 do
      # Auth (public)
      post "auth/register", to: "auth#register"
      post "auth/login",    to: "auth#login"

      # Tenant profile
      resource :tenant,        only: %i[show update]
      resource :tenant_config, only: %i[show update]

      # DIDs
      resources :dids, only: %i[index create update destroy]

      # Client workspaces and client-specific operations
      resources :client_workspaces, only: %i[index show create update] do
        collection do
          post :seed_starters
        end
        member do
          patch :knowledge
          get :availability
        end
        resources :number_requests, only: :create, controller: "mock_number_requests"
        resources :appointment_types, only: %i[index create update destroy]
        resources :availability_rules, only: %i[index create update destroy]
        resources :availability_exceptions, only: %i[index create update destroy]
        resources :appointments, only: %i[index create destroy]
      end

      # Call logs (read-only from dashboard)
      resources :call_logs, only: %i[index show]

      # Billing / PayPal subscriptions
      get    "billing",         to: "billing#show"
      post   "billing/confirm", to: "billing#confirm"
      delete "billing",         to: "billing#cancel"
      post   "billing/webhook", to: "billing#webhook"

      # Platform administration
      get "admin/overview", to: "admin#overview"
    end
  end

  # Health check
  get "up", to: proc { [200, {}, ["ok"]] }

  # Internal — used by agent/fs-bridge (authenticated by X-Internal-Token header)
  namespace :internal do
    get  "dids/:number/config",          to: "dids#show_config"
    get  "dids/:number/fs_gateway",      to: "dids#fs_gateway"
    get  "dids/:number/fs_dialplan",     to: "dids#fs_dialplan"
    get  "client_workspaces/:id/knowledge", to: "client_workspaces#knowledge"
    get  "client_workspaces/:id/appointment_types", to: "client_workspaces#appointment_types"
    post "client_workspaces/:id/availability", to: "client_workspaces#availability"
    post "client_workspaces/:id/appointments", to: "client_workspaces#appointments"
    post "freeswitch/xml",               to: "freeswitch#xml"
    post "freeswitch/cdr",               to: "freeswitch#cdr"
  end

  # Root — return API info instead of 404
  root to: proc { [200, { "Content-Type" => "application/json" }, ['{"status":"ok","service":"receptify-api","version":"v1"}']] }
end
