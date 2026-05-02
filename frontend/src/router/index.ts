import { createRouter, createWebHistory } from "vue-router";

import { pinia } from "@/stores";
import { useAuthStore } from "@/stores/auth";
import AdminVideosView from "@/views/AdminVideosView.vue";
import HomeView from "@/views/HomeView.vue";
import LoginView from "@/views/LoginView.vue";
import PublishView from "@/views/PublishView.vue";
import RegisterView from "@/views/RegisterView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      meta: {
        requiresAuth: true,
      },
    },
    {
      path: "/admin/videos",
      name: "admin-videos",
      component: AdminVideosView,
      meta: {
        requiresAuth: true,
        requiresAdmin: true,
      },
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/register",
      name: "register",
      component: RegisterView,
    },
    {
      path: "/publish",
      name: "publish",
      component: PublishView,
      meta: {
        requiresAuth: true,
      },
    },
  ],
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia);

  await authStore.hydrateSession();

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      name: "login",
      query: {
        redirect: to.fullPath,
      },
    };
  }

  if (to.meta.requiresAdmin && !authStore.currentUser?.is_admin) {
    return {
      name: "home",
    };
  }

  if ((to.name === "login" || to.name === "register") && authStore.isAuthenticated) {
    const redirect =
      typeof to.query.redirect === "string" && to.query.redirect ? to.query.redirect : "/";
    return redirect;
  }

  return true;
});
