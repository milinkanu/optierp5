<template>
  <div id="app">
    <router-view />
    <Toast />
  </div>
</template>

<script setup>
import Toast from './components/ui/Toast.vue'
</script>

<style>
#app {
  font-family: Inter, system-ui, sans-serif;
  min-height: 100vh;
  background: #f4f7fb;
}
</style>
