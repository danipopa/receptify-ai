module Api
  module V1
    class CallLogsController < BaseController
      def index
        page  = (params[:page] || 1).to_i
        limit = PAGINATION_DEFAULT_LIMIT
        scope = current_tenant.call_logs.recent
        scope = scope.where(direction: params[:direction]) if params[:direction].present?
        logs  = scope.offset((page - 1) * limit).limit(limit)
        render json: {
          call_logs: logs.as_json(only: %i[id caller_number direction duration started_at ended_at]),
          meta: { page: page, limit: limit, total: scope.count }
        }
      end

      def show
        log = current_tenant.call_logs.find(params[:id])
        render json: log.as_json(
          only: %i[id caller_number direction duration transcript summary started_at ended_at],
          include: { did: { only: %i[number provider] } }
        )
      end
    end
  end
end
