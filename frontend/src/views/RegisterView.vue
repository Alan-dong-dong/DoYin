<template>
  <main class="auth-shell auth-shell--centered">
    <section class="auth-shell__panel auth-shell__panel--form auth-shell__panel--compact">
      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="auth-form__header auth-form__header--centered">
          <p class="auth-form__kicker">DoYin 账号</p>
          <h2>创建账号</h2>
          <p>用一个新账号进入你的短视频工作区</p>
        </div>

        <p v-if="statusMessage" class="auth-form__notice" :data-tone="statusTone">
          {{ statusMessage }}
        </p>

        <label class="auth-form__field">
          <span>邮箱</span>
          <input
            v-model="email"
            type="email"
            name="email"
            autocomplete="email"
            placeholder="name@example.com"
            :aria-invalid="Boolean(fieldErrors.email)"
            @blur="validateField('email')"
          />
          <small v-if="fieldErrors.email" class="auth-form__field-error">
            {{ fieldErrors.email }}
          </small>
        </label>

        <label class="auth-form__field">
          <span>用户名</span>
          <input
            v-model="username"
            type="text"
            name="username"
            autocomplete="username"
            placeholder="输入公开用户名"
            maxlength="50"
            :aria-invalid="Boolean(fieldErrors.username)"
            @blur="validateField('username')"
          />
          <small v-if="fieldErrors.username" class="auth-form__field-error">
            {{ fieldErrors.username }}
          </small>
        </label>

        <label class="auth-form__field">
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            name="password"
            autocomplete="new-password"
            placeholder="设置密码"
            maxlength="255"
            :aria-invalid="Boolean(fieldErrors.password)"
            @blur="validateField('password')"
          />
          <small v-if="fieldErrors.password" class="auth-form__field-error">
            {{ fieldErrors.password }}
          </small>
        </label>

        <label class="auth-form__field">
          <span>确认密码</span>
          <input
            v-model="passwordConfirmation"
            type="password"
            name="password-confirmation"
            autocomplete="new-password"
            placeholder="再次输入密码"
            maxlength="255"
            :aria-invalid="Boolean(fieldErrors.passwordConfirmation)"
            @blur="validateField('passwordConfirmation')"
          />
          <small
            v-if="fieldErrors.passwordConfirmation"
            class="auth-form__field-error"
          >
            {{ fieldErrors.passwordConfirmation }}
          </small>
        </label>

        <button class="auth-form__submit" type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? "创建中..." : "创建账号" }}
        </button>

        <p class="auth-form__switch">
          已有账号？
          <RouterLink class="auth-form__switch-link" :to="{ name: 'login', query: loginLinkQuery }">
            去登录
          </RouterLink>
        </p>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

type FieldName = "email" | "username" | "password" | "passwordConfirmation";

interface RegisterFieldErrors {
  email: string | null;
  username: string | null;
  password: string | null;
  passwordConfirmation: string | null;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const { errorMessage: storeErrorMessage, isAuthenticating, isRegistering } = storeToRefs(authStore);

const email = ref("");
const username = ref("");
const password = ref("");
const passwordConfirmation = ref("");
const successMessage = ref<string | null>(null);
const localErrorMessage = ref<string | null>(null);
const fieldErrors = ref<RegisterFieldErrors>({
  email: null,
  username: null,
  password: null,
  passwordConfirmation: null,
});

const isSubmitting = computed(() => isRegistering.value || isAuthenticating.value);
const statusMessage = computed(
  () => successMessage.value ?? localErrorMessage.value ?? storeErrorMessage.value,
);
const statusTone = computed(() => (successMessage.value ? "success" : "error"));
const loginLinkQuery = computed(() => {
  const query: Record<string, string> = {};
  if (typeof route.query.redirect === "string" && route.query.redirect) {
    query.redirect = route.query.redirect;
  }

  return query;
});

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function normalizeUsername(value: string): string {
  return value.trim();
}

function getFieldError(field: FieldName): string | null {
  if (field === "email") {
    const normalizedEmail = normalizeEmail(email.value);
    if (!normalizedEmail) {
      return "请填写邮箱。";
    }

    if (normalizedEmail.length > 255) {
      return "邮箱不能超过 255 个字符。";
    }

    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      return "请输入有效的邮箱地址。";
    }
  }

  if (field === "username") {
    const normalizedUsername = normalizeUsername(username.value);
    if (!normalizedUsername) {
      return "请填写用户名。";
    }

    if (normalizedUsername.length > 50) {
      return "用户名不能超过 50 个字符。";
    }
  }

  if (field === "password") {
    if (!password.value) {
      return "请填写密码。";
    }

    if (password.value.length > 255) {
      return "密码不能超过 255 个字符。";
    }
  }

  if (field === "passwordConfirmation") {
    if (!passwordConfirmation.value) {
      return "请再次输入密码。";
    }

    if (passwordConfirmation.value !== password.value) {
      return "两次输入的密码不一致。";
    }
  }

  return null;
}

function validateField(field: FieldName): boolean {
  const nextError = getFieldError(field);
  fieldErrors.value[field] = nextError;
  return nextError === null;
}

function validateForm(): boolean {
  const fields: FieldName[] = ["email", "username", "password", "passwordConfirmation"];
  let isValid = true;

  for (const field of fields) {
    if (!validateField(field)) {
      isValid = false;
    }
  }

  return isValid;
}

async function handleSubmit() {
  successMessage.value = null;
  localErrorMessage.value = null;

  if (!validateForm()) {
    localErrorMessage.value = "请先修正高亮字段后再继续。";
    return;
  }

  try {
    const result = await authStore.registerAccount({
      email: normalizeEmail(email.value),
      username: normalizeUsername(username.value),
      password: password.value,
    });

    const redirect =
      typeof route.query.redirect === "string" && route.query.redirect
        ? route.query.redirect
        : "/";

    if (result.status === "signed_in") {
      successMessage.value = "账号已创建并登录。";
      await router.push(redirect);
      return;
    }

    await router.push({
      name: "login",
      query: {
        ...(typeof route.query.redirect === "string" && route.query.redirect
          ? { redirect: route.query.redirect }
          : {}),
        reason: "account-created",
        email: result.email,
      },
    });
  } catch {
    // The store exposes API failures for the form to render.
  }
}
</script>
