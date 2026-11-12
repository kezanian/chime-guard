// Chime Guard: Silent Google Cast Playback
// Automatically intercepts media_player & Music Assistant playback to absorb connect chimes.
// Subscribes dynamically to integration settings via Home Assistant WebSocket API.

(function () {
  "use strict";

  let CG_CONFIG = {
    mappings: {},
    min_mute_window: 1800,
    max_timeout: 12,
    external_takeover: true,
    intercept_join: true,
    excluded_speakers: [],
    known_ma_apps: ["sendspin", "music assistant", "mass", "dd107ddb"]
  };

  let configLoaded = false;

  const fetchConfig = function (hass) {
    if (!hass || !hass.connection) return;
    try {
      hass.connection.sendMessagePromise({ type: "chime_guard/config" })
        .then(function (result) {
          if (result) {
            CG_CONFIG = Object.assign(CG_CONFIG, result);
            configLoaded = true;
            console.info("[ChimeGuard] Configuration synced with Home Assistant:", CG_CONFIG);
          }
        })
        .catch(function (err) {
          console.debug("[ChimeGuard] Config fetch retry:", err);
        });
    } catch (e) {}
  };

  const getCastEntity = function (eid) {
    if (!eid || typeof eid !== "string") return null;
    if (CG_CONFIG.excluded_speakers && CG_CONFIG.excluded_speakers.includes(eid)) return null;

    if (CG_CONFIG.mappings && CG_CONFIG.mappings[eid]) {
      return CG_CONFIG.mappings[eid];
    }
    const rawEntities = Object.values(CG_CONFIG.mappings || {});
    if (rawEntities.includes(eid)) return eid;

    if (eid.endsWith("_2")) {
      const stripped = eid.slice(0, -2);
      if (rawEntities.includes(stripped)) return stripped;
    }
    return null;
  };

  const isMusicAssistantActive = function (castEnt) {
    try {
      const ha = document.querySelector("home-assistant");
      const liveHass = ha && ha.hass;
      if (!liveHass || !liveHass.states || !castEnt) return false;
      const st = liveHass.states[castEnt];
      if (!st || !st.attributes) return false;
      const app = (st.attributes.app_name || "").toLowerCase();
      const id = (st.attributes.app_id || "").toLowerCase();
      const known = CG_CONFIG.known_ma_apps || ["sendspin", "music assistant", "mass", "dd107ddb"];
      return known.some(k => app.includes(k) || id === k);
    } catch (e) {
      return false;
    }
  };

  const isColdStart = function (eid, castEnt) {
    try {
      const ha = document.querySelector("home-assistant");
      const liveHass = ha && ha.hass;
      if (!liveHass || !liveHass.states) return true;

      const maState = eid && liveHass.states[eid] ? liveHass.states[eid].state : "";
      const castState = castEnt && liveHass.states[castEnt] ? liveHass.states[castEnt].state : "";

      // 1. If physical Cast speaker is not playing or paused, it is a cold start
      if (castState !== "playing" && castState !== "paused") {
        return true;
      }

      // 2. Physical speaker is playing or paused.
      // If external takeover suppression is enabled and playing a non-MA source (e.g. Spotify from mobile):
      // Treat as OFF because Cast receiver handover will emit connect chime!
      if (CG_CONFIG.external_takeover && !isMusicAssistantActive(castEnt)) {
        return true;
      }

      // 3. Physical speaker is running Music Assistant.
      // If MA itself is playing or paused, this is an in-session track change/resume (no chime)
      if (maState === "playing" || maState === "paused") {
        return false;
      }

      return true;
    } catch (e) {
      return true;
    }
  };

  const muteAroundCall = async function (origCall, eid, castEnt, playFn) {
    if (!castEnt) return playFn ? playFn() : undefined;

    let result;
    try {
      await origCall("media_player", "volume_mute", { entity_id: castEnt, is_volume_muted: true });
    } catch (e) {
      console.warn("[ChimeGuard] mute error:", e);
    }

    if (playFn) {
      try {
        result = await playFn();
      } catch (e) {
        console.warn("[ChimeGuard] play error:", e);
      }
    }

    const unmute = function () {
      try {
        origCall("media_player", "volume_mute", { entity_id: castEnt, is_volume_muted: false });
      } catch (err) {}
    };

    const minMuteWindow = CG_CONFIG.min_mute_window || 1800;
    const maxTimeoutMs = (CG_CONFIG.max_timeout || 12) * 1000;

    const minMuteUntil = Date.now() + minMuteWindow;
    const deadline = Date.now() + maxTimeoutMs;

    const poll = function () {
      const curHa = document.querySelector("home-assistant");
      const curHass = curHa && curHa.hass;
      const curCast = curHass && curHass.states && curHass.states[castEnt];

      if (Date.now() >= minMuteUntil) {
        if (curCast && curCast.state === "playing") {
          unmute();
          return;
        }
      }

      if (Date.now() >= deadline) {
        unmute();
        return;
      }
      setTimeout(poll, 250);
    };

    setTimeout(poll, 250);
    return result;
  };

  const installChimeGuardHook = function () {
    try {
      const ha = document.querySelector("home-assistant");
      if (!ha) return false;
      if (ha.__chimeGuardInstalled) return true;
      ha.__chimeGuardInstalled = true;
      ha.__globalBeepHookInstalled = true;
      ha.__beepHookInstalled = true;

      const wrap = function (h) {
        if (!h || h.__chimeGuardWrapped) return h;
        if (!configLoaded) fetchConfig(h);

        const origCall = h.callService.bind(h);
        h.callService = async function (domain, service, data) {
          try {
            if (domain === "media_player") {
              const rawEid = data && (Array.isArray(data.entity_id) ? data.entity_id[0] : (data.entity_id || (Array.isArray(data.entities) ? data.entities[0] : null)));
              const castEnt = getCastEntity(rawEid);
              if (castEnt && isColdStart(rawEid, castEnt)) {
                if (["media_play", "media_play_pause", "turn_on", "toggle", "play_media"].includes(service)) {
                  return await muteAroundCall(origCall, rawEid, castEnt, function () { return origCall(domain, service, data); });
                }
              }

              if (service === "join" && CG_CONFIG.intercept_join) {
                const members = (data && data.group_members) || [];
                if (Array.isArray(members)) {
                  for (const m of members) {
                    const mCast = getCastEntity(m);
                    if (mCast && isColdStart(m, mCast)) {
                      muteAroundCall(origCall, m, mCast, null);
                    }
                  }
                }
              }
            } else if (domain === "mass" || domain === "music_assistant") {
              const rawEid = data && (Array.isArray(data.entity_id) ? data.entity_id[0] : (data.entity_id || data.entity || data.player));
              const castEnt = getCastEntity(rawEid);
              if (castEnt && isColdStart(rawEid, castEnt)) {
                return await muteAroundCall(origCall, rawEid, castEnt, function () { return origCall(domain, service, data); });
              }
            }
          } catch (e) {
            console.warn("[ChimeGuard] intercept error:", e);
          }
          return origCall(domain, service, data);
        };

        h.__chimeGuardWrapped = true;
        h.__globalBeepWrapped = true;
        h.__beepWrapped = true;
        return h;
      };

      if (ha.hass) wrap(ha.hass);

      try {
        const proto = Object.getPrototypeOf(ha);
        const desc = Object.getOwnPropertyDescriptor(proto, "hass") || Object.getOwnPropertyDescriptor(ha, "hass");
        if (desc && desc.set) {
          const origSet = desc.set;
          const origGet = desc.get;
          Object.defineProperty(ha, "hass", {
            configurable: true,
            enumerable: true,
            get: function () { return origGet.call(this); },
            set: function (val) {
              wrap(val);
              return origSet.call(this, val);
            }
          });
        }
      } catch (e) {}

      setInterval(function () {
        if (ha && ha.hass) wrap(ha.hass);
      }, 500);

      console.info("[ChimeGuard] Active: Silent Google Cast Protection installed.");
      return true;
    } catch (err) {
      console.warn("[ChimeGuard] init error:", err);
      return false;
    }
  };

  if (!installChimeGuardHook()) {
    if (window.customElements && window.customElements.whenDefined) {
      window.customElements.whenDefined("home-assistant").then(installChimeGuardHook);
    }
    const initTimer = setInterval(function () {
      if (installChimeGuardHook()) {
        clearInterval(initTimer);
      }
    }, 100);
  }
})();
