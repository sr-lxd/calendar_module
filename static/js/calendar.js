/**
 * Sofia Calendar Module JavaScript
 * Universal Calendar Generator Frontend Controller
 */

class SofiaCalendar {
    constructor() {
        this.currentYear = new Date().getFullYear();
        this.calendarData = null;
        this.isFullscreen = false;
        this.sessionId = localStorage.getItem('sofia_session_id') || this.generateSessionId();
        
        this.init();
    }
    
    generateSessionId() {
        const sessionId = 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
        localStorage.setItem('sofia_session_id', sessionId);
        return sessionId;
    }
    
    getRequestHeaders() {
        return {
            'Content-Type': 'application/json',
            'X-Session-ID': this.sessionId
        };
    }
    
    init() {
        this.bindEvents();
        this.loadSettings();
        this.bindHolidayEvents();
        this.initMobileOptimizations();
        this.fixModalScrollingForMobile();
    }

    // Fix mobile modal scrolling
    fixModalScrollingForMobile() {
        document.addEventListener('shown.bs.modal', () => {
            // Allow body scrolling on mobile
            document.body.style.overflow = '';
            document.body.style.position = '';
            document.body.style.paddingRight = '';

            // Disable calendar interaction when modal is open
            document.querySelectorAll('.calendar-year, .calendar-month, .calendar-day').forEach(el => {
                el.style.pointerEvents = 'none';
            });
        });

        document.addEventListener('hidden.bs.modal', () => {
            // Restore calendar interaction when modal is closed
            document.querySelectorAll('.calendar-year, .calendar-month, .calendar-day').forEach(el => {
                el.style.pointerEvents = '';
            });
        });
    }
    
    bindEvents() {
        // Year controls
        document.getElementById('current-year-btn').addEventListener('click', () => {
            document.getElementById('year-input').value = new Date().getFullYear();
        });
        
        document.getElementById('next-year-btn').addEventListener('click', () => {
            document.getElementById('year-input').value = new Date().getFullYear() + 1;
        });
        
        // Main action buttons
        document.getElementById('generate-btn').addEventListener('click', () => {
            this.generateCalendar();
        });
        
        document.getElementById('preview-btn').addEventListener('click', () => {
            this.previewCalendar();
        });
        
        document.getElementById('quick-generate').addEventListener('click', () => {
            this.generateCalendar();
        });
        
        // Export buttons
        document.querySelectorAll('.export-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const format = e.target.closest('.export-btn').dataset.format;
                this.exportCalendar(format);
            });
        });
        
        // Fullscreen toggle
        document.getElementById('fullscreen-btn').addEventListener('click', () => {
            this.toggleFullscreen();
        });
        
        // Feature options change handlers
        document.querySelectorAll('.form-check-input').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.saveSettings();
                
                // Auto-regenerate if calendar is already loaded and it's a display option
                if (this.calendarData && [
                    'show-festivals', 'show-lunar', 'show-lunar-festivals', 
                    'show-solar-terms', 'show-personal-holidays', 'show-auspicious'
                ].includes(checkbox.id)) {
                    console.log(`Display option ${checkbox.id} changed, regenerating calendar...`);
                    this.generateCalendar();
                }
            });
        });
    }
    
    loadSettings() {
        // Load saved settings from localStorage
        const settings = JSON.parse(localStorage.getItem('sofia_calendar_settings') || '{}');
        
        Object.keys(settings).forEach(key => {
            const element = document.getElementById(key);
            if (element && element.type === 'checkbox') {
                element.checked = settings[key];
            }
        });
    }
    
    saveSettings() {
        const settings = {};
        document.querySelectorAll('.form-check-input').forEach(checkbox => {
            settings[checkbox.id] = checkbox.checked;
        });
        
        localStorage.setItem('sofia_calendar_settings', JSON.stringify(settings));
    }
    
    getOptions() {
        return {
            show_festivals: document.getElementById('show-festivals').checked,
            show_lunar: document.getElementById('show-lunar').checked,
            show_lunar_festivals: document.getElementById('show-lunar-festivals').checked,
            show_solar_terms: document.getElementById('show-solar-terms').checked,
            show_personal_holidays: document.getElementById('show-personal-holidays').checked,
            show_auspicious: document.getElementById('show-auspicious').checked,
            highlight_today: document.getElementById('highlight-today').checked
        };
    }

    bindHolidayEvents() {
        // Add Holiday button
        document.getElementById('add-holiday-btn').addEventListener('click', () => {
            this.showAddHolidayModal();
        });
        
        // Manage Holidays button
        document.getElementById('manage-holidays-btn').addEventListener('click', () => {
            this.showManageHolidaysModal();
        });
        
        // Save Holiday button
        document.getElementById('save-holiday-btn').addEventListener('click', () => {
            this.saveHoliday();
        });
        
        // Month change handler for day population
        document.getElementById('holiday-month').addEventListener('change', () => {
            this.populateHolidayDays();
        });
        
        // Category change handler for icon suggestions
        document.getElementById('holiday-category').addEventListener('change', (e) => {
            this.suggestIconForCategory(e.target.value);
        });
    }
    
    async generateCalendar() {
        const year = parseInt(document.getElementById('year-input').value);
        const options = this.getOptions();
        
        if (year < 1900 || year > 2100) {
            this.showToast('请输入1900-2100之间的年份', 'warning');
            return;
        }
        
        this.showLoading(true);
        
        // Performance optimization: reduce payload on mobile
        if (this.isMobile && options.show_auspicious) {
            options.simplified_auspicious = true;  // Request simplified data for mobile
        }
        
        try {
            const response = await fetch('/calendar/api/generate', {
                method: 'POST',
                headers: this.getRequestHeaders(),
                body: JSON.stringify({ year, options })
            });
            
            if (!response.ok) {
                throw new Error('生成失败');
            }
            
            const data = await response.json();
            this.calendarData = data;
            
            // Use progressive rendering on mobile for better performance
            if (this.isMobile) {
                this.progressiveRenderCalendar(data);
            } else {
                this.renderCalendar(data);
            }
            
            this.updateTitle(year);
            this.showToast('年历生成成功！', 'success');
            
        } catch (error) {
            console.error('Error generating calendar:', error);
            this.showToast('生成年历时发生错误', 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    progressiveRenderCalendar(data) {
        const container = document.getElementById('calendar-container');
        container.innerHTML = '<div class="calendar-year"></div>';
        const calendarYear = container.querySelector('.calendar-year');
        
        // Render months progressively to avoid blocking UI
        let monthIndex = 0;
        const renderNextMonth = () => {
            if (monthIndex < data.data.months.length) {
                const monthData = data.data.months[monthIndex];
                const monthHtml = this.generateSingleMonthHtml(monthData, data.data.year);
                
                const monthElement = document.createElement('div');
                monthElement.innerHTML = monthHtml;
                calendarYear.appendChild(monthElement.firstElementChild);
                
                monthIndex++;
                
                // Use requestAnimationFrame for smooth rendering
                if (this.isMobile) {
                    requestAnimationFrame(renderNextMonth);
                } else {
                    setTimeout(renderNextMonth, 10);
                }
            } else {
                // All months rendered, add event handlers
                this.bindDayClickHandlers();
            }
        };
        
        renderNextMonth();
    }
    
    generateSingleMonthHtml(monthData, year) {
        const monthNames = [
            "", "一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"
        ];
        
        const daysHtml = this.generateDaysHtml(monthData.weeks);
        
        return `
            <div class="calendar-month">
                <div class="month-header">
                    ${monthNames[monthData.month]} ${year}
                </div>
                <div class="weekdays">
                    <div class="weekday">日</div>
                    <div class="weekday">一</div>
                    <div class="weekday">二</div>
                    <div class="weekday">三</div>
                    <div class="weekday">四</div>
                    <div class="weekday">五</div>
                    <div class="weekday">六</div>
                </div>
                <div class="calendar-days">
                    ${daysHtml}
                </div>
            </div>
        `;
    }
    
    async previewCalendar() {
        const year = parseInt(document.getElementById('year-input').value);
        const options = this.getOptions();
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/calendar/api/preview', {
                method: 'POST',
                headers: this.getRequestHeaders(),
                body: JSON.stringify({ year, options })
            });
            
            if (!response.ok) {
                throw new Error('预览失败');
            }
            
            const data = await response.json();
            
            // Open preview in new window with proper UTF-8 handling
            const previewWindow = window.open('', '_blank');
            
            // HTML content is now directly returned as string (no base64 decoding needed)
            const htmlContent = data.html_content;
            
            // Write HTML with proper encoding
            previewWindow.document.open();
            previewWindow.document.write(htmlContent);
            previewWindow.document.close();
            
            this.showToast('预览已在新窗口中打开', 'info');
            
        } catch (error) {
            console.error('Error previewing calendar:', error);
            this.showToast('预览年历时发生错误', 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    renderCalendar(data) {
        const container = document.getElementById('calendar-container');
        const monthsHtml = this.generateMonthsHtml(data.data);
        
        container.innerHTML = `
            <div class="calendar-year">
                ${monthsHtml}
            </div>
        `;
        
        // Add click handlers to calendar days
        this.bindDayClickHandlers();
    }
    
    generateMonthsHtml(calendarData) {
        const monthNames = [
            "", "一月", "二月", "三月", "四月", "五月", "六月",
            "七月", "八月", "九月", "十月", "十一月", "十二月"
        ];
        
        return calendarData.months.map(monthData => {
            const daysHtml = this.generateDaysHtml(monthData.weeks);
            
            return `
                <div class="calendar-month">
                    <div class="month-header">
                        ${monthNames[monthData.month]} ${calendarData.year}
                    </div>
                    <div class="weekdays">
                        <div class="weekday">日</div>
                        <div class="weekday">一</div>
                        <div class="weekday">二</div>
                        <div class="weekday">三</div>
                        <div class="weekday">四</div>
                        <div class="weekday">五</div>
                        <div class="weekday">六</div>
                    </div>
                    <div class="calendar-days">
                        ${daysHtml}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    generateDaysHtml(weeks) {
        return weeks.map(week => {
            return week.map(dayData => {
                if (!dayData) {
                    return '<div class="calendar-day other-month"></div>';
                }
                
                const classes = ['calendar-day'];
                if (dayData.is_today) classes.push('today');
                if (dayData.is_weekend) classes.push('weekend');
                
                const eventsHtml = dayData.events.map(event => {
                    let eventClass = `day-event ${event.type}`;
                    let eventStyle = '';
                    let eventContent = event.name;
                    let clickHandler = '';
                    
                    // Special handling for personal holidays
                    if (event.type === 'personal_holiday') {
                        if (event.color) {
                            eventStyle = `style="color: ${event.color}; border-left-color: ${event.color};"`;
                        }
                        if (event.icon) {
                            eventContent = `${event.icon} ${event.name}`;
                        }
                        if (event.is_birthday) {
                            eventClass += ' birthday-event';
                        }
                    }
                    
                    // Special handling for auspicious events
                    if (event.type === 'auspicious') {
                        clickHandler = `onclick="event.stopPropagation(); window.sofiaCalendar.showAuspiciousDetail(${JSON.stringify(event).replace(/"/g, '&quot;')})"`;
                    }
                    
                    return `<div class="${eventClass}" ${eventStyle} ${clickHandler}>${eventContent}</div>`;
                }).join('');
                
                return `
                    <div class="${classes.join(' ')}" 
                         data-date="${dayData.date}"
                         data-day-info='${JSON.stringify(dayData)}'>
                        <div class="day-number">${dayData.day}</div>
                        <div class="day-events">${eventsHtml}</div>
                    </div>
                `;
            }).join('');
        }).join('');
    }
    
    bindDayClickHandlers() {
        document.querySelectorAll('.calendar-day[data-day-info]').forEach(dayElement => {
            dayElement.addEventListener('click', (e) => {
                const dayInfo = JSON.parse(e.target.closest('.calendar-day').dataset.dayInfo);
                this.showDayDetail(dayInfo);
            });
        });
    }
    
    // Utility method to ensure modal visibility in fullscreen mode
    ensureModalVisibility(modalElement) {
        if (document.querySelector('.fullscreen-calendar')) {
            // 在全屏模式下，确保模态框有正确的z-index
            modalElement.style.zIndex = '10000';
            
            // 也为backdrop设置z-index
            modalElement.addEventListener('shown.bs.modal', () => {
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.style.zIndex = '9999';
                }
            }, { once: true });
        }
    }

    showDayDetail(dayInfo) {
        const modal = new bootstrap.Modal(document.getElementById('dayDetailModal'));
        const modalElement = document.getElementById('dayDetailModal');
        
        // 确保在全屏模式下模态框可见
        this.ensureModalVisibility(modalElement);
        
        const title = document.getElementById('dayDetailTitle');
        const body = document.getElementById('dayDetailBody');
        
        // Format date
        const date = new Date(dayInfo.date);
        const dateStr = date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long'
        });
        
        title.innerHTML = `<i class="fas fa-calendar-day me-2"></i>${dateStr}`;
        
        // Generate detail content
        let detailHtml = '';
        
        // Events section
        if (dayInfo.events && dayInfo.events.length > 0) {
            dayInfo.events.forEach(event => {
                detailHtml += this.generateEventDetailHtml(event);
            });
        } else {
            detailHtml = '<p class="text-muted">这一天没有特殊信息。</p>';
        }
        
        body.innerHTML = detailHtml;
        modal.show();
    }
    
    showAuspiciousDetail(event) {
        const modal = new bootstrap.Modal(document.getElementById('dayDetailModal'));
        const modalElement = document.getElementById('dayDetailModal');
        
        // 确保在全屏模式下模态框可见
        this.ensureModalVisibility(modalElement);
        
        const title = document.getElementById('dayDetailTitle');
        const body = document.getElementById('dayDetailBody');
        
        title.innerHTML = `<i class="fas fa-yin-yang text-purple me-2"></i>黄道吉日详情`;
        
        // Generate auspicious detail content
        let detailHtml = this.generateEventDetailHtml(event);
        
        body.innerHTML = detailHtml;
        modal.show();
    }
    
    generateEventDetailHtml(event) {
        switch (event.type) {
            case 'festival':
                return `
                    <div class="day-detail-section">
                        <h6><i class="fas fa-star text-danger me-2"></i>节日</h6>
                        <p class="mb-0">${event.name}</p>
                    </div>
                `;
            
            case 'personal_holiday':
                const iconHtml = event.icon ? event.icon : '🎉';
                const colorStyle = event.color ? `style="color: ${event.color}"` : '';
                const descHtml = event.description ? `<p class="text-muted small mb-1">${event.description}</p>` : '';
                const categoryHtml = event.category ? `<small class="badge bg-secondary">${this.getCategoryName(event.category)}</small>` : '';
                
                return `
                    <div class="day-detail-section">
                        <h6><span ${colorStyle}>${iconHtml}</span> 个性化节日</h6>
                        <p class="mb-1">${event.name} ${categoryHtml}</p>
                        ${descHtml}
                    </div>
                `;
            
            case 'lunar':
                return `
                    <div class="day-detail-section">
                        <h6><i class="fas fa-moon text-success me-2"></i>农历</h6>
                        <p class="mb-0">${event.name}</p>
                    </div>
                `;
            
            case 'lunar_festival':
                return `
                    <div class="day-detail-section">
                        <h6><i class="fas fa-lantern text-warning me-2"></i>农历节日</h6>
                        <p class="mb-0">${event.name}</p>
                    </div>
                `;
            
            case 'solar_term':
                return `
                    <div class="day-detail-section">
                        <h6><i class="fas fa-leaf text-info me-2"></i>节气</h6>
                        <p class="mb-0">${event.name}</p>
                    </div>
                `;
            
            case 'auspicious':
                if (event.details) {
                    const details = event.details;
                    
                    // 基础信息
                    let basicInfo = `
                        <div class="auspicious-basic-info">
                            <div class="row">
                                <div class="col-4"><strong>日干支:</strong> ${details.ganzhi || ''}</div>
                                <div class="col-4"><strong>建星:</strong> ${details.star || ''}</div>
                                <div class="col-4"><strong>黄道神:</strong> ${details.god || ''}</div>
                            </div>
                            <div class="row mt-2">
                                <div class="col-4"><strong>年干支:</strong> ${details.year_ganzhi || ''}</div>
                                <div class="col-4"><strong>月干支:</strong> ${details.month_ganzhi || ''}</div>
                                <div class="col-4"><strong>吉凶:</strong> 
                                    <span class="badge bg-${details.auspicious_level?.color || 'secondary'}">
                                        ${details.auspicious_level?.level || ''}
                                    </span>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // 农历信息
                    let lunarInfo = '';
                    if (details.lunar_info) {
                        const lunar = details.lunar_info;
                        lunarInfo = `
                            <div class="lunar-info mt-3">
                                <h6><i class="fas fa-moon text-success me-2"></i>农历信息</h6>
                                <p>农历${lunar.year}年${lunar.month}月${lunar.day}日${lunar.is_leap ? '(闰月)' : ''}</p>
                            </div>
                        `;
                    }
                    
                    // 传统元素
                    let traditionalInfo = '';
                    if (details.chong_sha || details.peng_zu || details.tai_shen) {
                        traditionalInfo = `
                            <div class="traditional-info mt-3">
                                <h6><i class="fas fa-yin-yang text-purple me-2"></i>传统信息</h6>
                                ${details.chong_sha ? `<p><strong>冲煞:</strong> ${details.chong_sha}</p>` : ''}
                                ${details.tai_shen ? `<p><strong>胎神:</strong> ${details.tai_shen}</p>` : ''}
                                ${details.peng_zu ? `
                                    <div class="peng-zu-info">
                                        <strong>彭祖百忌:</strong>
                                        <small class="d-block text-muted">${details.peng_zu.stem_taboo || ''}</small>
                                        <small class="d-block text-muted">${details.peng_zu.branch_taboo || ''}</small>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }
                    
                    // 宜事详情
                    let yiDetails = '';
                    if (details.yi && details.yi.length > 0) {
                        const yiItems = details.yi.map(item => {
                            if (typeof item === 'object' && item.name) {
                                return `
                                    <div class="activity-item mb-2">
                                        <strong class="text-success">${item.name}</strong>
                                        <small class="d-block text-muted">${item.description || ''}</small>
                                    </div>
                                `;
                            }
                            return `<span class="activity-tag yi-tag me-1">${item}</span>`;
                        }).join('');
                        
                        yiDetails = `
                            <div class="yi-section mt-3">
                                <h6><i class="fas fa-check-circle text-success me-2"></i>宜事 (${details.yi.length}项)</h6>
                                <div class="yi-content">${yiItems}</div>
                            </div>
                        `;
                    }
                    
                    // 忌事详情
                    let jiDetails = '';
                    if (details.ji && details.ji.length > 0) {
                        const jiItems = details.ji.map(item => {
                            if (typeof item === 'object' && item.name) {
                                return `
                                    <div class="activity-item mb-2">
                                        <strong class="text-danger">${item.name}</strong>
                                        <small class="d-block text-muted">${item.description || ''}</small>
                                    </div>
                                `;
                            }
                            return `<span class="activity-tag ji-tag me-1">${item}</span>`;
                        }).join('');
                        
                        jiDetails = `
                            <div class="ji-section mt-3">
                                <h6><i class="fas fa-times-circle text-danger me-2"></i>忌事 (${details.ji.length}项)</h6>
                                <div class="ji-content">${jiItems}</div>
                            </div>
                        `;
                    }
                    
                    return `
                        <div class="day-detail-section auspicious-info">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6 class="mb-0">
                                    <i class="fas fa-yin-yang text-purple me-2"></i>黄道吉日详情
                                </h6>
                                <a href="/calendar/help/auspicious" target="_blank" 
                                   class="btn btn-outline-info btn-sm">
                                    <i class="fas fa-question-circle me-1"></i>
                                    计算原理
                                </a>
                            </div>
                            ${basicInfo}
                            ${lunarInfo}
                            ${traditionalInfo}
                            ${yiDetails}
                            ${jiDetails}
                        </div>
                    `;
                }
                return `
                    <div class="day-detail-section">
                        <h6><i class="fas fa-yin-yang text-purple me-2"></i>黄道吉日</h6>
                        <p class="mb-0">${event.name}</p>
                    </div>
                `;
            
            default:
                return `
                    <div class="day-detail-section">
                        <h6><i class="fas fa-info-circle me-2"></i>信息</h6>
                        <p class="mb-0">${event.name}</p>
                    </div>
                `;
        }
    }
    
    async exportCalendar(format) {
        const year = parseInt(document.getElementById('year-input').value);
        const options = this.getOptions();
        
        if (!this.calendarData) {
            this.showToast('请先生成年历', 'warning');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch(`/calendar/api/export/${format}`, {
                method: 'POST',
                headers: this.getRequestHeaders(),
                body: JSON.stringify({ year, options })
            });
            
            if (!response.ok) {
                throw new Error('导出失败');
            }
            
            // Handle file download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            a.href = url;
            a.download = `${year}年历.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showToast(`${format.toUpperCase()}文件下载成功！`, 'success');
            
        } catch (error) {
            console.error('Export error:', error);
            this.showToast(`导出${format.toUpperCase()}时发生错误`, 'danger');
        } finally {
            this.showLoading(false);
        }
    }
    
    toggleFullscreen() {
        const calendarDisplay = document.querySelector('.calendar-display');
        const fullscreenBtn = document.getElementById('fullscreen-btn');
        
        if (!this.isFullscreen) {
            calendarDisplay.classList.add('fullscreen-calendar');
            fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
            this.isFullscreen = true;
        } else {
            calendarDisplay.classList.remove('fullscreen-calendar');
            fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
            this.isFullscreen = false;
        }
    }
    
    updateTitle(year) {
        document.getElementById('calendar-title').innerHTML = 
            `<i class="fas fa-calendar me-2"></i>${year}年年历`;
    }
    
    showLoading(show) {
        const spinner = document.getElementById('loading-spinner');
        const container = document.getElementById('calendar-container');
        
        if (show) {
            spinner.style.display = 'block';
            container.style.opacity = '0.5';
        } else {
            spinner.style.display = 'none';
            container.style.opacity = '1';
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.getElementById('notification-toast');
        const toastBody = document.getElementById('toast-message');
        
        // 确保在全屏模式下Toast可见
        if (document.querySelector('.fullscreen-calendar')) {
            toast.style.zIndex = '10002';
        }
        
        // Set message and style
        toastBody.textContent = message;
        toast.className = `toast bg-${type === 'danger' ? 'danger' : type} text-white`;
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    // Personal Holiday Management Methods
    showAddHolidayModal() {
        const modal = new bootstrap.Modal(document.getElementById('addHolidayModal'));
        const modalElement = document.getElementById('addHolidayModal');
        
        // 确保在全屏模式下模态框可见
        this.ensureModalVisibility(modalElement);
        
        this.clearHolidayForm();
        this.populateHolidayDays(); // Initialize days dropdown
        modal.show();
    }

    async showManageHolidaysModal() {
        const modal = new bootstrap.Modal(document.getElementById('manageHolidaysModal'));
        const modalElement = document.getElementById('manageHolidaysModal');
        
        // 确保在全屏模式下模态框可见
        this.ensureModalVisibility(modalElement);
        
        await this.loadHolidaysList();
        modal.show();
    }

    clearHolidayForm() {
        document.getElementById('holiday-form').reset();
        document.getElementById('holiday-color').value = '#ff6b6b';
        document.getElementById('holiday-icon').value = '🎉';
        document.getElementById('holiday-category').value = 'personal';
    }

    populateHolidayDays() {
        const monthSelect = document.getElementById('holiday-month');
        const daySelect = document.getElementById('holiday-day');
        const selectedMonth = parseInt(monthSelect.value);

        daySelect.innerHTML = '<option value="">选择日期</option>';

        if (selectedMonth) {
            const daysInMonth = new Date(2024, selectedMonth, 0).getDate();
            for (let day = 1; day <= daysInMonth; day++) {
                const option = document.createElement('option');
                option.value = day;
                option.textContent = `${day}日`;
                daySelect.appendChild(option);
            }
        }
    }

    suggestIconForCategory(category) {
        const iconInput = document.getElementById('holiday-icon');
        const colorInput = document.getElementById('holiday-color');
        
        const suggestions = {
            'personal': { icon: '🎉', color: '#ff6b6b' },
            'birthday': { icon: '🎂', color: '#ff69b4' },
            'anniversary': { icon: '💕', color: '#ff1493' },
            'work': { icon: '💼', color: '#4169e1' },
            'family': { icon: '👨‍👩‍👧‍👦', color: '#ffa500' },
            'other': { icon: '⭐', color: '#20b2aa' }
        };

        if (suggestions[category]) {
            iconInput.value = suggestions[category].icon;
            colorInput.value = suggestions[category].color;
        }
    }

    async saveHoliday() {
        const form = document.getElementById('holiday-form');
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const holidayData = {
            name: document.getElementById('holiday-name').value,
            month: parseInt(document.getElementById('holiday-month').value),
            day: parseInt(document.getElementById('holiday-day').value),
            description: document.getElementById('holiday-description').value,
            category: document.getElementById('holiday-category').value,
            color: document.getElementById('holiday-color').value,
            icon: document.getElementById('holiday-icon').value,
            is_birthday: document.getElementById('holiday-is-birthday').checked
        };

        try {
            const response = await fetch('/calendar/api/personal-holidays', {
                method: 'POST',
                headers: this.getRequestHeaders(),
                body: JSON.stringify(holidayData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '保存失败');
            }

            const result = await response.json();
            this.showToast('个性化节日添加成功！', 'success');
            
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('addHolidayModal')).hide();
            
            // Refresh calendar if it's already generated
            if (this.calendarData) {
                this.generateCalendar();
            }

        } catch (error) {
            console.error('Save holiday error:', error);
            this.showToast(error.message || '添加节日时发生错误', 'danger');
        }
    }

    async loadHolidaysList() {
        const listContainer = document.getElementById('holidays-list');
        const year = parseInt(document.getElementById('year-input').value);
        
        listContainer.innerHTML = `
            <div class="text-center py-3">
                <i class="fas fa-spinner fa-spin"></i>
                正在加载节日列表...
            </div>
        `;

        try {
            const response = await fetch(`/calendar/api/personal-holidays?year=${year}`, {
                headers: this.getRequestHeaders()
            });
            
            if (!response.ok) {
                throw new Error('获取节日列表失败');
            }

            const data = await response.json();
            const holidays = data.holidays || [];

            if (holidays.length === 0) {
                listContainer.innerHTML = `
                    <div class="text-center py-4">
                        <i class="fas fa-heart-broken text-muted mb-3" style="font-size: 2rem;"></i>
                        <p class="text-muted">还没有添加任何个性化节日</p>
                        <button class="btn btn-primary btn-sm" onclick="window.sofiaCalendar.showAddHolidayModal()" data-bs-dismiss="modal">
                            <i class="fas fa-plus me-1"></i>
                            添加第一个节日
                        </button>
                    </div>
                `;
                return;
            }

            const holidaysHtml = holidays.map(holiday => this.generateHolidayItemHtml(holiday)).join('');
            listContainer.innerHTML = `
                <div class="holidays-list">
                    ${holidaysHtml}
                </div>
            `;

        } catch (error) {
            console.error('Load holidays error:', error);
            listContainer.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 2rem;"></i>
                    <p class="text-muted">加载节日列表时发生错误</p>
                    <button class="btn btn-outline-secondary btn-sm" onclick="window.sofiaCalendar.loadHolidaysList()">
                        <i class="fas fa-refresh me-1"></i>
                        重新加载
                    </button>
                </div>
            `;
        }
    }

    generateHolidayItemHtml(holiday) {
        const iconStyle = holiday.color ? `style="color: ${holiday.color}"` : '';
        const categoryName = this.getCategoryName(holiday.category);
        
        return `
            <div class="holiday-item mb-3 p-3 border rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <span ${iconStyle}>${holiday.icon || '🎉'}</span>
                            ${holiday.name}
                            <small class="badge bg-secondary ms-2">${categoryName}</small>
                        </h6>
                        <p class="text-muted small mb-1">
                            <i class="fas fa-calendar me-1"></i>
                            ${holiday.month}月${holiday.day}日
                            ${holiday.is_birthday ? ' • 生日' : ''}
                        </p>
                        ${holiday.description ? `<p class="text-muted small mb-0">${holiday.description}</p>` : ''}
                    </div>
                    <div class="btn-group-vertical btn-group-sm">
                        <button class="btn btn-outline-danger btn-sm" 
                                onclick="window.sofiaCalendar.deleteHoliday(${holiday.id})"
                                title="删除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    async deleteHoliday(holidayId) {
        if (!confirm('确定要删除这个个性化节日吗？')) {
            return;
        }

        try {
            const response = await fetch(`/calendar/api/personal-holidays/${holidayId}`, {
                method: 'DELETE',
                headers: this.getRequestHeaders()
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || '删除失败');
            }

            const result = await response.json();
            this.showToast(result.message || '节日删除成功', 'success');
            await this.loadHolidaysList(); // Reload the list
            
            // Refresh calendar if it's already generated
            if (this.calendarData) {
                this.generateCalendar();
            }

        } catch (error) {
            console.error('Delete holiday error:', error);
            this.showToast(error.message || '删除节日时发生错误', 'danger');
        }
    }

    getCategoryName(category) {
        const categoryNames = {
            'personal': '个人',
            'birthday': '生日',
            'anniversary': '纪念日',
            'work': '工作',
            'family': '家庭',
            'other': '其他'
        };
        return categoryNames[category] || '未分类';
    }

    // Mobile Optimization Methods
    initMobileOptimizations() {
        // Detect mobile device
        this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        this.isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        if (this.isMobile || this.isTouch) {
            this.setupTouchInteractions();
            this.optimizeForMobile();
        }
        
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 300);
        });
        
        // Optimize viewport for mobile
        this.optimizeViewport();
    }
    
    setupTouchInteractions() {
        // Improve touch responsiveness for calendar days
        document.addEventListener('touchstart', (e) => {
            const calendarDay = e.target.closest('.calendar-day');
            if (calendarDay) {
                calendarDay.classList.add('touch-active');
                setTimeout(() => {
                    calendarDay.classList.remove('touch-active');
                }, 150);
            }
        });
        
        // Add swipe support for month navigation (future enhancement)
        let touchStartX = 0;
        let touchStartY = 0;
        
        document.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        });
        
        document.addEventListener('touchmove', (e) => {
            // Prevent default scrolling for horizontal swipes
            const touchX = e.touches[0].clientX;
            const touchY = e.touches[0].clientY;
            const deltaX = Math.abs(touchX - touchStartX);
            const deltaY = Math.abs(touchY - touchStartY);
            
            if (deltaX > deltaY && deltaX > 10) {
                e.preventDefault();
            }
        }, { passive: false });
        
        // Optimize form interactions for mobile
        this.optimizeMobileFormInteractions();
    }
    
    optimizeForMobile() {
        // Add mobile-specific CSS classes
        document.body.classList.add('mobile-optimized');
        
        // Reduce animation duration for mobile
        const style = document.createElement('style');
        style.textContent = `
            @media (max-width: 768px) {
                .calendar-month {
                    animation-duration: 0.3s !important;
                }
                .calendar-day {
                    transition-duration: 0.1s !important;
                }
                .touch-active {
                    background-color: #e3f2fd !important;
                    transform: scale(0.95) !important;
                }
            }
        `;
        document.head.appendChild(style);
        
        // Optimize loading indicators for mobile
        this.optimizeMobileLoading();
    }
    
    optimizeMobileFormInteractions() {
        // Improve form focus behavior on mobile
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                // Scroll element into view with padding
                setTimeout(() => {
                    input.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center',
                        inline: 'nearest'
                    });
                }, 300);
            });
        });
        
        // Improve checkbox interactions
        const checkboxes = document.querySelectorAll('.form-check-input');
        checkboxes.forEach(checkbox => {
            const label = checkbox.closest('.form-check').querySelector('.form-check-label');
            if (label) {
                label.addEventListener('touchend', (e) => {
                    e.preventDefault();
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                });
            }
        });
    }
    
    optimizeMobileLoading() {
        // Show loading indicator immediately on mobile
        const originalShowLoading = this.showLoading.bind(this);
        this.showLoading = function(show) {
            if (show && this.isMobile) {
                // Add haptic feedback if available
                if (navigator.vibrate) {
                    navigator.vibrate(50);
                }
            }
            originalShowLoading(show);
        }.bind(this);
    }
    
    handleOrientationChange() {
        // Recalculate layout after orientation change
        const calendarContainer = document.getElementById('calendar-container');
        if (calendarContainer) {
            // Force reflow
            calendarContainer.style.opacity = '0.99';
            setTimeout(() => {
                calendarContainer.style.opacity = '1';
            }, 50);
        }
        
        // Adjust modal positioning if open
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            const modalDialog = openModal.querySelector('.modal-dialog');
            if (modalDialog) {
                modalDialog.style.marginTop = '10px';
                modalDialog.style.marginBottom = '10px';
            }
        }
    }
    
    optimizeViewport() {
        // Set optimal viewport for mobile
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
        
        // Add mobile theme color
        let themeColor = document.querySelector('meta[name="theme-color"]');
        if (!themeColor) {
            themeColor = document.createElement('meta');
            themeColor.name = 'theme-color';
            document.head.appendChild(themeColor);
        }
        themeColor.content = '#667eea';
    }
    
    // Enhanced toast for mobile
    showToast(message, type = 'info') {
        const toast = document.getElementById('notification-toast');
        const toastBody = document.getElementById('toast-message');
        
        // Set message and style
        toastBody.textContent = message;
        toast.className = `toast bg-${type === 'danger' ? 'danger' : type} text-white`;
        
        // Mobile-specific positioning
        if (this.isMobile) {
            toast.style.position = 'fixed';
            toast.style.top = '10px';
            toast.style.left = '50%';
            toast.style.transform = 'translateX(-50%)';
            toast.style.zIndex = '9999';
            toast.style.minWidth = '280px';
            
            // Add haptic feedback
            if (navigator.vibrate && type === 'success') {
                navigator.vibrate([50, 30, 50]);
            }
        }
        
        // Show toast
        const bsToast = new bootstrap.Toast(toast, {
            delay: this.isMobile ? 3000 : 4000  // Shorter delay on mobile
        });
        bsToast.show();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.sofiaCalendar = new SofiaCalendar();
});

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}