module JsonWebToken
  SECRET = ENV.fetch("JWT_SECRET") { raise "JWT_SECRET env var is required" }
  ALGORITHM = "HS256"
  EXPIRY = 24.hours

  def self.encode(payload, exp = EXPIRY.from_now)
    payload[:exp] = exp.to_i
    JWT.encode(payload, SECRET, ALGORITHM)
  end

  def self.decode(token)
    decoded = JWT.decode(token, SECRET, true, { algorithm: ALGORITHM })
    HashWithIndifferentAccess.new(decoded.first)
  rescue JWT::DecodeError => e
    raise AuthenticationError, "Invalid token: #{e.message}"
  end
end
