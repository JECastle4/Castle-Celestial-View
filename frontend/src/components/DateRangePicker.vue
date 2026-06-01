<template>
  <div class="date-range-picker">
    <div class="calendar">
      <label :for="idPrefix + '-start'">{{ t('forms.labels.startDate') }}</label>
      <input :id="idPrefix + '-start'" type="date" v-model="startDateString" @change="validateDates" />
    </div>
    <div class="calendar">
      <label :for="idPrefix + '-end'">{{ t('forms.labels.endDate') }}</label>
      <input :id="idPrefix + '-end'" type="date" v-model="endDateString" @change="validateDates" />
    </div>
    <div v-if="errorMessage" class="error-message">
      <span class="error-icon" aria-label="Error">&#9888;</span>
      {{ errorMessage }}
    </div>
    <button :disabled="!isValid" @click="applyDates">
      <i class="fa fa-sync" aria-hidden="true" style="margin-right: 0.5em;"></i>
      {{ t('buttons.apply') }}
    </button>
  </div>
</template>

<script lang="ts">
import '@fortawesome/fontawesome-free/css/all.min.css';
import { defineComponent, ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';

let instanceCounter = 0;

export default defineComponent({
  name: 'DateRangePicker',
  props: {
    initialStartDate: { type: String, required: true },
    initialEndDate: { type: String, required: true }
  },
  emits: ['update:dates'],
  setup(props, { emit }) {
    const { t } = useI18n();
    const idPrefix = `drp-${++instanceCounter}`;
    const startDateString = ref(props.initialStartDate);
    const endDateString = ref(props.initialEndDate);
    const errorMessage = ref('');
    const isValid = computed(() => {
      if (!startDateString.value || !endDateString.value) return false;
      const start = new Date(startDateString.value);
      const end = new Date(endDateString.value);
      return start <= end;
    });

    const validateDates = () => {
      if (!startDateString.value || !endDateString.value) {
        errorMessage.value = '';
        return;
      }
      const start = new Date(startDateString.value);
      const end = new Date(endDateString.value);
      if (start > end) {
        errorMessage.value = t('validation.startBeforeEnd');
      } else {
        errorMessage.value = '';
      }
    };

    const applyDates = () => {
      if (isValid.value) {
        emit('update:dates', {
          start: new Date(startDateString.value),
          end: new Date(endDateString.value)
        });
      }
    };

    // Emit initial dates on mount
    onMounted(() => {
      if (isValid.value) {
        emit('update:dates', {
          start: new Date(startDateString.value),
          end: new Date(endDateString.value)
        });
      }
    });

    return {
      idPrefix,
      startDateString,
      endDateString,
      errorMessage,
      isValid,
      validateDates,
      applyDates,
      t
    };
  }
});
</script>

<style scoped>
.date-range-picker {
  display: flex;
  gap: 2rem;
  justify-content: center;
  align-items: flex-start;
  flex-wrap: wrap;
}
.calendar {
  display: flex;
  flex-direction: column;
  align-items: center;
}
label {
  margin-bottom: 0.5rem;
}
.error-message {
  color: #d32f2f;
  display: flex;
  align-items: center;
  margin-top: 1rem;
  font-size: 1rem;
}
.error-icon {
  margin-right: 0.5rem;
  font-size: 1.2rem;
}
button {
  margin-top: 1rem;
  margin-bottom: 4rem;
  padding: 0.5rem 1.5rem;
  font-size: 1rem;
  border-radius: 4px;
  border: none;
  background: #0d47a1;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s;
}
button:disabled {
  background: #bdbdbd;
  cursor: not-allowed;
}
</style>
