<template>
  <main class="auth-shell auth-shell--centered">
    <section class="auth-shell__panel auth-shell__panel--form auth-shell__panel--compact">
      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="auth-form__header auth-form__header--centered">
          <p class="auth-form__kicker">DoYin 账号</p>
          <h2>登录 DoYin</h2>
          <p>继续你的短视频工作区</p>
        </div>

        <p
          v-if="sessionNoticeMessage"
          class="auth-form__notice"
          :data-tone="sessionNoticeTone"
        >
          {{ sessionNoticeMessage }}
        </p>

        <label class="auth-form__field">
          <span>邮箱</span>
          <input
            v-model="email"
            type="email"
            name="email"
            autocomplete="email"
            placeholder="name@example.com"
            required
          />
        </label>

        <label class="auth-form__field">
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            name="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            required
          />
        </label>

        <p v-if="errorMessage" class="auth-form__error" role="alert">
          {{ errorMessage }}
        </p>

        <button class="auth-form__submit" type="submit" :disabled="isAuthenticating">
          {{ isAuthenticating ? "登录中..." : "登录" }}
        </button>

        <p class="auth-form__switch">
          还没有账号？
          <RouterLink
            class="auth-form__switch-link"
            :to="{ name: 'register', query: registerLinkQuery }"
          >
            去注册
          </RouterLink>
        </p>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const {
  errorMessage: storeErrorMessage,
  isAuthenticating,
  registrationFallbackEmail,
  registrationNotice,
} = storeToRefs(authStore);

const email = ref("");
const password = ref("");
const localErrorMessage = ref<string | null>(null);

const errorMessage = computed(() => localErrorMessage.value ?? storeErrorMessage.value);
const sessionNoticeMessage = computed(() => {
  if (route.query.reason === "session-expired") {
    return "登录状态已过期，请重新登录后继续。";
  }

  if (route.query.reason === "account-created") {
    return registrationNotice.value ?? "账号已创建，请使用新账号登录。";
  }

  return null;
});
const sessionNoticeTone = computed(() =>
  route.query.reason === "account-created" ? "success" : undefined,
);
const registerLinkQuery = computed(() => {
  const query: Record<string, string> = {};
  if (typeof route.query.redirect === "string" && route.query.redirect) {
    query.redirect = route.query.redirect;
  }

  return query;
});

watch(
  () => [route.query.email, registrationFallbackEmail.value] as const,
  ([queryEmail, fallbackEmail]) => {
    const nextEmail =
      typeof queryEmail === "string" && queryEmail ? queryEmail : fallbackEmail;

    if (nextEmail) {
      email.value = nextEmail;
    }
  },
  { immediate: true },
);

async function handleSubmit() {
  localErrorMessage.value = null;

  if (!email.value.trim() || !password.value) {
    localErrorMessage.value = "请填写邮箱和密码。";
    return;
  }

  try {
    await authStore.signIn({
      email: email.value.trim(),
      password: password.value,
    });
    const redirect =
      typeof route.query.redirect === "string" && route.query.redirect
        ? route.query.redirect
        : "/";
    await router.push(redirect);
  } catch {
    // The store exposes the API error message for the form to render.
  }
}
</script>
