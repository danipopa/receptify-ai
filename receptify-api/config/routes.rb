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

      # Call logs (read-only from dashboard)
      resources :call_logs, only: %i[index show]

      # Billing / PayPal subscriptions
      get    "billing",         to: "billing#show"
      post   "billing/confirm", to: "billing#confirm"
      delete "billing",         to: "billing#cancel"
      post   "billing/webhook", to: "billing#webhook"
    end
  end

  # Health check
  get "up", to: proc { [200, {}, ["ok"]] }

  # Internal — used by agent/fs-bridge (authenticated by X-Internal-Token header)
  namespace :internal do
    get  "dids/:number/config",          to: "dids#config"
    get  "dids/:number/fs_gateway",      to: "dids#fs_gateway"
    get  "dids/:number/fs_dialplan",     to: "dids#fs_dialplan"
    post "freeswitch/xml",               to: "freeswitch#xml"
    post "freeswitch/cdr",               to: "freeswitch#cdr"
  end

  # Root — return API info instead of 404
  root to: proc { [200, { "Content-Type" => "application/json" }, ['{"status":"okk","service":"receptify-api","version":"v1"}']] }
end
