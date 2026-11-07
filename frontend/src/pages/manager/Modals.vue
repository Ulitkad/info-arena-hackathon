<script setup>
import { inject } from 'vue';
import Modal from '../../components/Modal.vue';
import Icon from '../../components/Icon.vue';
import ColorPicker from '../../components/ColorPicker.vue';
import InviteQrModal from '../../components/InviteQrModal.vue';
import { frameStyles } from '../../constants/frameStyles';
const manager = inject('manager-page');
const { store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, editReward, deleteReward, openRename, saveRename } = manager;
</script>

<template>
    <Modal v-if="modal === 'group'" title="Новая группа" @close="modal = ''"
      ><form
        class="modal-form"
        @submit.prevent="createGroup"
      >
        <label class="field-label"
          >Название группы<input
            v-model.trim="groupName"
            required
            maxlength="100"
            placeholder="Например, ИС-21" /></label
        ><button class="btn primary modal-submit">Создать группу</button>
      </form></Modal
    >
    <Modal
      v-else-if="modal === 'subject'"
      title="Новый предмет"
      @close="modal = ''"
      ><form
        class="modal-form"
        @submit.prevent="createSubject"
      >
        <label class="field-label"
          >Название предмета<input
            v-model.trim="subjectName"
            required
            maxlength="100"
            placeholder="Например, Программирование" /></label
         ><label class="field-label"
           >Цвет предмета<ColorPicker v-model="subjectColor" /></label
        ><button class="btn primary modal-submit">Добавить предмет</button>
      </form></Modal
    >
    <Modal
      v-else-if="modal === 'rename'"
      :title="`Переименовать ${renameTarget?.kind === 'group' ? 'группу' : 'предмет'}`"
      @close="modal = ''"
      ><form class="modal-form" @submit.prevent="saveRename">
        <label class="field-label">Новое название<input v-model.trim="renameName" maxlength="100" required /></label>
        <div class="modal-submit-row"><button type="button" class="btn secondary" @click="modal = ''">Отмена</button><button class="btn primary" :disabled="store.saving">Сохранить <Icon name="check" :size="15" /></button></div>
      </form></Modal
    >
    <Modal
      v-else-if="modal.startsWith('links:')"
      :title="`Предметы · ${inviteGroup?.name || ''}`"
      @close="modal = ''"
      ><fieldset class="modal-form choice-field">
        <legend>Выбери предметы, которые изучает группа</legend>
        <label
          v-for="subject in catalog.subjects"
          :key="subject.id"
          class="check-option"
          ><input
            type="checkbox"
            :checked="
              catalog.links.some(
                (l) =>
                  l.group_id === inviteGroup.id && l.subject_id === subject.id,
              )
            "
            @change="toggleLink(inviteGroup.id, subject.id)"
          /><span class="fake-check"><Icon name="check" :size="13" /></span
          ><i class="subject-tiny" :style="{ background: subject.color }"></i
          >{{ subject.name }}</label
        >
        <p v-if="!catalog.subjects.length" class="muted">
          Сначала добавь предметы учреждения.
        </p>
      </fieldset></Modal
    >
    <Modal
      v-else-if="modal === 'invite-student'"
      title="Приглашение для ученика"
      @close="modal = ''"
      ><div class="modal-form">
        <p>
          Ссылка группы создаст заявку на вступление. Группа будет
          активирована после модерации.
        </p>
        <label class="field-label"
          >Группа<select v-model="assign.group_id" required>
            <option disabled value="">Выбери группу</option>
            <option
              v-for="group in catalog.groups"
              :key="group.id"
              :value="String(group.id)"
            >
              {{ group.name }}
            </option>
          </select></label
        ><button
          class="btn primary modal-submit"
          :disabled="!assign.group_id || store.saving"
          @click="invite('STUDENT', Number(assign.group_id))"
        >
          <Icon name="link" :size="16" />Создать и скопировать ссылку
        </button>
      </div></Modal
    >
    <Modal
      v-else-if="modal === 'invite-result'"
      title="Приглашение готово"
      @close="modal = ''"
     ><div class="modal-form"><p>{{ inviteRole === 'STUDENT' ? 'Отправьте ссылку ученикам. Она многоразовая, вступление — после модерации.' : 'Отправьте ссылку преподавателю. Она одноразовая: первый активировавший её пользователь получит выбранную нагрузку, после чего ссылка перестанет работать.' }}</p><label class="field-label">Ссылка приглашения<input :value="inviteUrl" readonly @focus="$event.target.select()" /></label><div class="button-row wrap"><button class="btn primary" @click="copyInvite">Скопировать ссылку</button><button class="btn secondary" @click="modal = 'invite-qr'"><Icon name="qr-code" :size="16" />Показать QR-код</button></div></div></Modal>
     <InviteQrModal v-else-if="modal === 'invite-qr'" :url="inviteUrl" @close="modal = ''" />
    <Modal
      v-else-if="modal === 'teacher'"
      :title="editingTeacher ? 'Учебная нагрузка' : 'Приглашение преподавателя'"
      wide
      @close="modal = ''"
      ><div class="modal-form">
        <p v-if="editingTeacher">{{ editingTeacher.display_name }} — выберите предметы и группы.</p>
        <p v-else>Выберите предметы и группы для будущего преподавателя. Приглашение одноразовое и перестанет работать после активации.</p>
        <p v-if="!catalog.links.length">Сначала создайте предметы и группы и привяжите предметы к группам.</p>
        <div
          v-for="subject in catalog.subjects"
          :key="subject.id"
          class="matrix-subject"
        >
          <span class="matrix-dot" :style="{ background: subject.color }"></span
          ><strong>{{ subject.name }}</strong>
          <div class="matrix-groups">
            <label
              v-for="group in catalog.groups.filter((g) =>
                catalog.links.some(
                  (l) => l.group_id === g.id && l.subject_id === subject.id,
                ),
              )"
              :key="group.id"
              ><input
                v-model="assign.loads"
                type="checkbox"
                :value="`${subject.id}:${group.id}`"
              /><span>{{ group.name }}</span></label
            >
          </div>
        </div>
        <button
          class="btn primary modal-submit"
          :disabled="!assign.loads.length || store.saving"
          @click="editingTeacher ? saveTeacherLoads() : invite('TEACHER')"
        >
          <Icon name="link" :size="16" />{{
            editingTeacher ? 'Сохранить нагрузку' : 'Создать и скопировать ссылку'
          }}
        </button>
      </div></Modal
    >
    <Modal
      v-else-if="modal === 'reward'"
      :title="editRewardId ? 'Изменить награду' : 'Новая награда'"
      @close="modal = ''"
      ><form class="modal-form" @submit.prevent="saveReward">
        <label v-if="reward.kind !== 'FRAME'" class="field-label"
          >Название<input
            v-model.trim="reward.name"
            maxlength="100"
            required
            placeholder="Например, Исследователь"
        /></label>
        <div v-else class="field-label frame-style-field"><span>Стиль рамки</span><div class="frame-style-grid"><label v-for="style in frameStyles" :key="style.id" class="frame-style-option" :class="{ selected: reward.frame_style === style.id }"><input v-model="reward.frame_style" type="radio" :value="style.id" required @change="reward.name = style.name" /><span class="avatar frame-style-swatch" :class="`frame-${style.id}`"><Icon :name="style.icon" :size="18" /></span><span><strong>{{ style.name }}</strong><small>{{ style.description }}</small></span><Icon v-if="reward.frame_style === style.id" name="check" :size="14" class="selected-check" /></label></div></div>
        <div class="form-grid">
          <label class="field-label"
            >Тип награды<select v-model="reward.kind" @change="reward.frame_style = reward.kind === 'FRAME' ? (reward.frame_style || frameStyles[0].id) : null; reward.name = reward.kind === 'FRAME' ? (frameStyles.find(item => item.id === reward.frame_style)?.name || '') : reward.name">
               <option value="TITLE">Звание</option>
              <option value="FRAME">Рамка профиля</option>
              <option value="CUSTOM">Своя награда</option>
            </select></label
          ><label class="field-label"
            >Нужно баллов<input
              v-model.number="reward.threshold"
              type="number"
              min="1"
              max="100000"
              required
          /></label>
        </div>
         <p class="muted">Награда будет добавлена в выбранный боевой пропуск.</p><label class="field-label"
          >Символ<select v-model="reward.icon">
            <option
              v-for="name in [
                'award',
                'sparkles',
                'crown',
                'flame',
                'swords',
                'star',
                'shield',
              ]"
              :key="name"
              :value="name"
            >
              {{ name }}
            </option>
          </select></label
        ><button class="btn primary modal-submit" :disabled="store.saving">
          {{ editRewardId ? "Сохранить" : "Создать награду" }}
          <Icon name="check" :size="15" />
        </button></form
    ></Modal>
</template>
