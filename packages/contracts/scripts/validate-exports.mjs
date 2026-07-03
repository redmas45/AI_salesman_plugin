import { ACTIONS, ACTION_PARAMS, ACTION_EVENT_STATUSES, API_PATHS, WS_MESSAGES } from "../index.js";

const requiredGroups = {
  ACTIONS,
  ACTION_PARAMS,
  ACTION_EVENT_STATUSES,
  API_PATHS,
  WS_MESSAGES,
};

for (const [groupName, group] of Object.entries(requiredGroups)) {
  if (!group || typeof group !== "object" || !Object.keys(group).length) {
    throw new Error(`${groupName} must export a non-empty object.`);
  }
}

process.stdout.write("Shared contracts validated.\n");
