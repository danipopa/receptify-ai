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
    end
  end

  # Health check
  get "up", to: proc { [200, {}, ["ok"]] }
end
