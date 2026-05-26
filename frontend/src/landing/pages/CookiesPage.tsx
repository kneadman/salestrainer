import React from "react";
import { Link } from "react-router-dom";

const CookiesPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#0f1729] text-[#94a3b8] font-inter">
      <div className="max-w-[800px] mx-auto px-4 sm:px-6 py-12 lg:py-16">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-[13px] text-[#5eead4] hover:underline mb-8 transition-colors"
        >
          ← На главную
        </Link>
        <h1 className="font-manrope text-[28px] sm:text-[32px] font-bold text-[#e2e8f0] mb-8 leading-tight">
          Политика использования файлов cookie
        </h1>

        <div className="space-y-8 text-[14px] leading-relaxed">
          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">1. Что такое cookie</h2>
            <p>
              Cookie — это небольшие текстовые файлы, которые веб-сайт сохраняет на вашем компьютере или мобильном устройстве при посещении сайта. Они позволяют сайту запоминать ваши действия и предпочтения (такие как логин, язык, размер шрифта и другие настройки отображения) в течение некоторого времени, чтобы вам не приходилось вводить их повторно при повторном посещении сайта или переходе с одной страницы на другую.
            </p>
          </section>

          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">2. Какие cookie мы используем</h2>
            <p>На нашем Сервисе мы используем следующие категории cookie:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>
                <strong className="text-[#e2e8f0]">Необходимые (технические) cookie.</strong> Эти файлы необходимы для корректной работы Сервиса. Они обеспечивают базовые функции, такие как навигация по страницам и доступ к защищённым областям сайта. Без этих cookie Сервис не может функционировать надлежащим образом.
              </li>
              <li>
                <strong className="text-[#e2e8f0]">Функциональные cookie.</strong> Позволяют запоминать выбор, который вы делаете (например, ваше имя пользователя, язык или регион), и предоставлять расширенные, более персональные функции.
              </li>
              <li>
                <strong className="text-[#e2e8f0]">Аналитические (статистические) cookie.</strong> Помогают нам понять, как посетители взаимодействуют с Сервисом, собирая и сообщая информацию анонимно. Это позволяет нам улучшать работу сайта.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">3. Цели использования cookie</h2>
            <p>Мы используем cookie для следующих целей:</p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li>обеспечение корректной работы Сервиса и его функциональных возможностей;</li>
              <li>аутентификация и авторизация Пользователей;</li>
              <li>сохранение предпочтений и настроек Пользователя;</li>
              <li>сбор обезличенной статистики и аналитики посещаемости;</li>
              <li>улучшение производительности и удобства использования Сервиса.</li>
            </ul>
          </section>

          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">4. Управление cookie</h2>
            <p>
              Большинство веб-браузеров позволяют вам управлять cookie через настройки браузера. Вы можете удалить существующие cookie или заблокировать сохранение новых. Обратите внимание, что отключение cookie может повлиять на функциональность Сервиса и привести к тому, что некоторые разделы сайта будут работать некорректно.
            </p>
            <p className="mt-2">
              Инструкции по управлению cookie для популярных браузеров:
            </p>
            <ul className="list-disc pl-5 space-y-1 mt-2">
              <li><a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener noreferrer" className="text-[#5eead4] hover:underline">Google Chrome</a></li>
              <li><a href="https://support.mozilla.org/ru/kb/ukazatel-otklyucheniya-cookie" target="_blank" rel="noopener noreferrer" className="text-[#5eead4] hover:underline">Mozilla Firefox</a></li>
              <li><a href="https://support.microsoft.com/ru-ru/help/17442/windows-internet-explorer-delete-manage-cookies" target="_blank" rel="noopener noreferrer" className="text-[#5eead4] hover:underline">Microsoft Edge</a></li>
              <li><a href="https://support.apple.com/ru-ru/guide/safari/sfri11471/mac" target="_blank" rel="noopener noreferrer" className="text-[#5eead4] hover:underline">Safari</a></li>
            </ul>
          </section>

          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">5. Согласие на использование cookie</h2>
            <p>
              При первом посещении Сервиса Пользователю отображается уведомление об использовании cookie. Продолжая использовать Сервис и нажимая кнопку согласия, Пользователь подтверждает своё согласие на использование cookie в соответствии с настоящей Политикой.
            </p>
            <p className="mt-2">
              Если Пользователь не согласен с использованием cookie, он должен прекратить использование Сервиса или изменить настройки браузера для блокировки cookie.
            </p>
          </section>

          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">6. Изменения политики</h2>
            <p>
              Оператор оставляет за собой право вносить изменения в настоящую Политику использования файлов cookie. Все изменения вступают в силу с момента их публикации на сайте. Пользователю рекомендуется периодически просматривать данную Политику для ознакомления с актуальной версией.
            </p>
          </section>

          <section>
            <h2 className="font-manrope text-[18px] font-semibold text-[#e2e8f0] mb-3">7. Контактная информация</h2>
            <p>
              По всем вопросам, связанным с использованием cookie, Пользователь может связаться с Оператором через форму обратной связи на сайте.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
};

export default React.memo(CookiesPage);
