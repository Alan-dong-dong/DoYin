import { createApp } from "vue";

import App from "./App.vue";
import { setUnauthorizedHandler } from "./lib/api";
import { router } from "./router";
import { pinia } from "./stores";
import { useAuthStore } from "./stores/auth";
import "./styles.css";

const app = createApp(App);

app.use(pinia);
app.use(router);

const authStore = useAuthStore(pinia);
void authStore.hydrateSession();

let isRecoveringUnauthorizedSession = false;
setUnauthorizedHandler(async () => {
  if (isRecoveringUnauthorizedSession) {
    return;
  }

  isRecoveringUnauthorizedSession = true;
  authStore.clearSession();

  try {
    const currentRoute = router.currentRoute.value;
    if (currentRoute.name === "login") {
      return;
    }

    await router.push({
      name: "login",
      query: {
        redirect: currentRoute.fullPath || "/",
        reason: "session-expired",
      },
    });
  } finally {
    isRecoveringUnauthorizedSession = false;
  }
});

app.mount("#app");
