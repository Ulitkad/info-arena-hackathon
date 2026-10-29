import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: '/', component: () => import('./pages/Home.vue'), meta: { title: 'Моя арена', roles: ['STUDENT'] } },
    { path: '/battlepass/:id?', component: () => import('./pages/Battlepass.vue'), meta: { title: 'Боевые пропуски', roles: ['STUDENT'] } },
    { path: '/arena', component: () => import('./pages/Arena.vue'), meta: { title: 'Инфо-арена', roles: ['STUDENT'] } },
    { path: '/friends', component: () => import('./pages/Friends.vue'), meta: { title: 'Друзья и дуэли', roles: ['STUDENT'] } },
    { path: '/users/:id', component: () => import('./pages/Profile.vue'), meta: { title: 'Профиль участника', roles: ['STUDENT'] } },
    { path: '/settings', component: () => import('./pages/Settings.vue'), meta: { title: 'Мой стиль', roles: ['STUDENT'] } },
    { path: '/notifications', component: () => import('./pages/Notifications.vue'), meta: { title: 'Уведомления', roles: ['STUDENT', 'TEACHER', 'MANAGER', 'ADMIN'] } },
    { path: '/teach', component: () => import('./pages/Teacher.vue'), meta: { title: 'Пространство преподавателя', roles: ['TEACHER'] } },
    { path: '/manage/:tab?', component: () => import('./pages/Manager.vue'), meta: { title: 'Управление учреждением', roles: ['MANAGER', 'ADMIN'] } },
    { path: '/admin', component: () => import('./pages/Admin.vue'), meta: { title: 'Учебные учреждения', roles: ['ADMIN'] } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
