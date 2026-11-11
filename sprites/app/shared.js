(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.SpritesShared = factory();
  }
}(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function isValidConcept(c) {
    return typeof c === "string" && c.length > 0;
  }

  function isValidIv(iv) {
    return Number.isInteger(iv) && iv >= 0;
  }

  function isValidHex(hex) {
    return typeof hex === "string" && /^#[0-9a-f]{6}$/i.test(hex);
  }

  function isPlainObject(o) {
    return o !== null && typeof o === "object" && !Array.isArray(o);
  }

  function mergeCast(localCast, shared, hasWaypoint) {
    const local = (isPlainObject(localCast) && isPlainObject(localCast.projects)) 
      ? localCast 
      : { projects: {} };

    if (!hasWaypoint || !isPlainObject(shared)) {
      const result = { projects: {} };
      for (const key in local.projects) {
        result.projects[key] = { ...local.projects[key] };
      }
      return result;
    }

    const result = {
      projects: {}
    };

    for (const key in local.projects) {
      result.projects[key] = { ...local.projects[key] };
    }

    if (isPlainObject(shared.projects)) {
      for (const key in shared.projects) {
        const sProj = shared.projects[key];
        if (!isPlainObject(sProj)) continue;

        const target = result.projects[key] || {};
        const updated = { ...target };

        if (isValidConcept(sProj.concept)) updated.concept = sProj.concept;
        if (isValidIv(sProj.iv)) updated.iv = sProj.iv;
        if (isValidHex(sProj.hex)) updated.hex = sProj.hex.toUpperCase();

        result.projects[key] = updated;
      }
    }

    return result;
  }

  function mergeBehaviors(localBehaviors, shared, hasWaypoint) {
    if (!isPlainObject(localBehaviors)) {
      return {};
    }

    if (!hasWaypoint || !isPlainObject(shared)) {
      return { ...localBehaviors };
    }

    const result = { ...localBehaviors };
    const sBeh = shared.behaviors;

    if (isPlainObject(sBeh)) {
      for (const key in sBeh) {
        if (Object.prototype.hasOwnProperty.call(localBehaviors, key)) {
          const localVal = localBehaviors[key];
          const sharedVal = sBeh[key];
          if (typeof localVal === typeof sharedVal) {
            result[key] = sharedVal;
          }
        }
      }
    }

    return result;
  }

  function setProject(shared, key, patch) {
    const result = (isPlainObject(shared)) 
      ? { ...shared } 
      : { schema: "sprites.shared", version: 1, projects: {}, behaviors: {} };
    
    result.schema = "sprites.shared";
    result.version = 1;
    result.projects = (isPlainObject(result.projects)) 
      ? { ...result.projects } 
      : {};

    if (typeof key !== "string" || !/^[a-z0-9][a-z0-9._-]*$/.test(key)) {
      // Must return new objects for projects and behaviors to avoid mutation of input shared
      if (isPlainObject(result.projects)) {
        result.projects = { ...result.projects };
        for (const k in result.projects) {
          if (isPlainObject(result.projects[k])) {
            result.projects[k] = { ...result.projects[k] };
          }
        }
      }
      if (isPlainObject(result.behaviors)) {
        result.behaviors = { ...result.behaviors };
      }
      return result;
    }

    const projectEntry = { ...result.projects[key] };
    if (isPlainObject(patch)) {
      if (isValidConcept(patch.concept)) projectEntry.concept = patch.concept;
      if (isValidIv(patch.iv)) projectEntry.iv = patch.iv;
      if (isValidHex(patch.hex)) projectEntry.hex = patch.hex.toUpperCase();
    }

    result.projects[key] = projectEntry;

    return result;
  }

  return {
    mergeCast: mergeCast,
    mergeBehaviors: mergeBehaviors,
    setProject: setProject
  };
}));
