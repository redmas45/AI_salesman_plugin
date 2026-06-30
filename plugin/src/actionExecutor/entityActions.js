import { ACTIONS, ACTION_PARAMS, DEFAULT_ENTITY_RECOMMENDATION_TITLE } from "../constants";
import { entityIdsFromParams, openEntityDetail, showEntityOverlay, sortEntityOverlay } from "../entityOverlay";

export function canExecuteEntityAction(action) {
  return (
    action.action === ACTIONS.SHOW_ENTITIES ||
    action.action === ACTIONS.COMPARE_ENTITIES ||
    action.action === ACTIONS.OPEN_ENTITY_DETAIL ||
    action.action === ACTIONS.SORT_ENTITIES
  );
}

export async function executeEntityAction(action) {
  if (action.action === ACTIONS.SHOW_ENTITIES || action.action === ACTIONS.COMPARE_ENTITIES) {
    return showEntities(action.parameters || {});
  }
  if (action.action === ACTIONS.OPEN_ENTITY_DETAIL) {
    return openEntityDetail(action.parameters?.[ACTION_PARAMS.ENTITY_ID] || action.parameters?.id);
  }
  if (action.action === ACTIONS.SORT_ENTITIES) {
    return sortEntityOverlay(action.parameters || {});
  }
  return false;
}

function showEntities(params) {
  return showEntityOverlay(
    entityIdsFromParams(params),
    params[ACTION_PARAMS.SEARCH_QUERY] || params.title || DEFAULT_ENTITY_RECOMMENDATION_TITLE,
  );
}
