<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const password = ref('')
const error = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(password.value)
    router.push('/snapshot')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-shell">
    <div class="login-box">
      <h1>KASTARA FINANCE</h1>
      <p class="src">Masuk dengan password dashboard.</p>
      <input
        v-model="password" type="password" placeholder="Password" autofocus
        @keyup.enter="submit"
      >
      <button class="btn" style="width:100%" :disabled="loading" @click="submit">
        {{ loading ? 'Memeriksa...' : 'Masuk' }}
      </button>
      <p v-if="error" class="src" style="color:var(--fail);margin-top:8px">{{ error }}</p>
      <p v-if="!auth.passwordConfigured" class="src" style="color:var(--skip);margin-top:8px">
        DASHBOARD_PASSWORD belum di-set di .env — isi dulu sebelum bisa login.
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-box {
  width: 280px;
  padding: 24px;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.login-box h1 {
  font-size: 16px;
  margin: 0 0 4px;
  letter-spacing: .5px;
}
.login-box input {
  margin: 14px 0 10px;
}
</style>
