class ApplicationController < ActionController::API
  rescue_from AuthenticationError, with: :unauthorized
  rescue_from ActiveRecord::RecordNotFound, with: :not_found
  rescue_from ActiveRecord::RecordInvalid, with: :unprocessable

  private

  def unauthorized(e)
    render json: { error: e.message }, status: :unauthorized
  end

  def not_found(e)
    render json: { error: e.message }, status: :not_found
  end

  def unprocessable(e)
    render json: { errors: e.record.errors.full_messages }, status: :unprocessable_entity
  end
end
