# Be sure to restart your server when you modify this file.

Rails.application.config.middleware.insert_before 0, Rack::Cors do
  allow do
    origins do |source, _env|
      if Rails.env.development?
        # Allow any localhost port in development
        source =~ /\Ahttp:\/\/localhost(:\d+)?\z/
      else
        allowed = ENV.fetch("ALLOWED_ORIGINS", "https://app.receptify.us").split(",").map(&:strip)
        allowed.include?(source)
      end
    end

    resource "*",
      headers: :any,
      methods: [:get, :post, :put, :patch, :delete, :options, :head],
      expose: ["Authorization"]
  end
end
