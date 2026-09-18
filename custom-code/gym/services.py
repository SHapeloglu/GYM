"""
PaymentService — iyzico checkout entegrasyonunun tek giriş noktası.

Tasarım kararı (bkz. ARCHITECTURE.md "Sprint 2 — iyzico Entegrasyon Planı"):
- iyzipay SDK çağrısı TEK bir metodun (_call_iyzico_checkout) arkasında izole
  edilir. Görünüm katmanı (views_api.py) veya başka hiçbir yer SDK'yı
  doğrudan import etmez.
- iyzico'nun yanıtı ayrıştırılmaz (alan alan parse edilmez); olduğu gibi
  Payment.raw_response JSONField'ına yazılır. Bu alan zaten bu amaç için
  ayrılmıştı (bkz. ARCHITECTURE.md gym_payment tablosu notu).
- Sandbox anahtarları tanımlı değilse (henüz iyzico hesabı açılmadığı için),
  servis otomatik olarak MOCK modda çalışır: gerçek SDK'ya hiç dokunmadan,
  SDK'nın gerçek yanıt şeklini taklit eden sahte bir yanıt üretir. Gerçek
  anahtarlar geldiğinde tek değişiklik ortam değişkenleridir — bu dosyada
  hiçbir satır değişmez.

Kullanım:
    from wger.gym.services import PaymentService

    payment, checkout_info = PaymentService.create_checkout(membership, amount)
    # payment: yeni oluşturulan Payment kaydı (status='pending')
    # checkout_info: {'checkoutFormContent': ..., 'paymentPageUrl': ..., 'token': ...}
"""
import hashlib
import hmac
import logging
import uuid
from decimal import Decimal

from django.conf import settings

from wger.gym.models.new_models import Payment

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """iyzico çağrısı sırasında oluşan, çağırana taşınması gereken hatalar için."""
    pass


class PaymentService:
    """
    Tüm iyzico ödeme akışının tek girişi. checkout/webhook/refund view'ları
    bu sınıfın metodlarını çağırır, iyzipay SDK'sını asla doğrudan çağırmaz.
    """

    _REQUIRED_SETTINGS = ('IYZICO_API_KEY', 'IYZICO_SECRET_KEY', 'IYZICO_BASE_URL')

    @classmethod
    def is_mock_mode(cls):
        """
        iyzico anahtarları tanımlı değilse True döner. Gerçek anahtarlar
        main.py'ye/prod.env'e eklenip container yeniden başlatılınca bu
        otomatik olarak False'a döner — kodda hiçbir değişiklik gerekmez.
        """
        return not all(getattr(settings, key, None) for key in cls._REQUIRED_SETTINGS)

    @classmethod
    def create_checkout(cls, membership, amount=None, callback_url=None):
        """
        Bir üyelik için ödeme başlatır.

        Args:
            membership: wger.gym.models.new_models.Membership instance'ı.
                        Payment.membership FK'si buraya bağlanır.
            amount: Decimal veya str. Verilmezse membership.package.price
                    kullanılır.
            callback_url: iyzico'nun ödeme sonrası yönlendireceği URL.
                          Verilmezse settings.IYZICO_CALLBACK_URL kullanılır.

        Returns:
            (payment, checkout_info) tuple'ı.

        Raises:
            PaymentServiceError: iyzico çağrısı başarısız olursa. Bu durumda
                Payment kaydı yine de status='failed' ile oluşturulmuş olur
                (audit trail için) ve raw_response hata detayını içerir.
        """
        if amount is None:
            amount = membership.package.price

        conversation_id = str(uuid.uuid4())

        payment = Payment.objects.create(
            membership=membership,
            amount=amount,
            payment_method=Payment.Method.IYZICO,
            status=Payment.Status.PENDING,
            transaction_id=conversation_id,
        )

        try:
            raw_response = cls._call_iyzico_checkout(
                conversation_id=conversation_id,
                amount=amount,
                membership=membership,
                callback_url=callback_url or getattr(settings, 'IYZICO_CALLBACK_URL', ''),
            )
        except Exception as exc:
            logger.exception('iyzico checkout başlatma hatası (conversation_id=%s)', conversation_id)
            payment.status = Payment.Status.FAILED
            payment.raw_response = {'error': str(exc)}
            payment.save(update_fields=['status', 'raw_response', 'updated_at'])
            raise PaymentServiceError(str(exc)) from exc

        payment.raw_response = raw_response
        payment.save(update_fields=['raw_response', 'updated_at'])

        checkout_info = {
            'checkoutFormContent': raw_response.get('checkoutFormContent'),
            'paymentPageUrl': raw_response.get('paymentPageUrl'),
            'token': raw_response.get('token'),
        }
        return payment, checkout_info

    @classmethod
    def _call_iyzico_checkout(cls, conversation_id, amount, membership, callback_url):
        """
        iyzipay SDK'sına gerçek çağrının yapıldığı (veya mock moddaysa
        taklit edildiği) TEK yer. Başka hiçbir yerden çağrılmamalı.
        """
        if cls.is_mock_mode():
            return cls._mock_checkout_response(conversation_id, amount)

        import iyzipay  # Sadece burada import edilir — mock modda hiç yüklenmez.
        import json

        options = {
            'api_key': settings.IYZICO_API_KEY,
            'secret_key': settings.IYZICO_SECRET_KEY,
            'base_url': settings.IYZICO_BASE_URL,
        }

        user = membership.user
        request_data = {
            'locale': 'tr',
            'conversationId': conversation_id,
            'price': str(amount),
            'paidPrice': str(amount),
            'currency': 'TRY',
            'basketId': f'membership-{membership.id}',
            'paymentGroup': 'SUBSCRIPTION',
            'callbackUrl': callback_url,
            'buyer': {
                'id': str(user.id),
                'name': user.first_name or user.username,
                'surname': user.last_name or '-',
                'email': user.email or 'noemail@gym.local',
                # NOT: iyzico'nun zorunlu tuttuğu ama elimizde henüz gerçek
                # veri olmayan alanlar. Sandbox anahtarları gelince gerçek
                # kullanıcı profili alanlarıyla doldurulmalı.
                'identityNumber': '11111111111',
                'registrationAddress': 'Adres bilgisi eklenmeli',
                'ip': '127.0.0.1',
                'city': 'Istanbul',
                'country': 'Turkey',
            },
            'billingAddress': {
                'contactName': user.get_full_name() or user.username,
                'city': 'Istanbul',
                'country': 'Turkey',
                'address': 'Adres bilgisi eklenmeli',
            },
            'basketItems': [
                {
                    'id': f'package-{membership.package_id}',
                    'name': membership.package.name,
                    'category1': 'Gym Membership',
                    'itemType': 'VIRTUAL',
                    'price': str(amount),
                }
            ],
        }

        checkout_form_initialize = iyzipay.CheckoutFormInitialize()
        response = checkout_form_initialize.create(request_data, options)
        raw = json.loads(response.read().decode('utf-8'))

        if raw.get('status') != 'success':
            raise PaymentServiceError(raw.get('errorMessage', 'iyzico checkout başlatılamadı'))

        return raw

    @staticmethod
    def _mock_checkout_response(conversation_id, amount):
        """
        Gerçek iyzico CheckoutFormInitialize yanıtının şeklini taklit eder.
        Alan adları iyzico'nun gerçek API dokümantasyonuyla birebir aynı
        tutulmalı ki gerçek anahtarlar geldiğinde çağıran kod hiç değişmesin.
        """
        fake_token = f'mock-token-{conversation_id[:8]}'
        logger.warning(
            'PaymentService MOCK modda çalışıyor — IYZICO_API_KEY/SECRET_KEY '
            'tanımlı değil. conversation_id=%s, amount=%s', conversation_id, amount
        )
        return {
            'status': 'success',
            'locale': 'tr',
            'conversationId': conversation_id,
            'token': fake_token,
            'checkoutFormContent': (
                f'<!-- MOCK: gerçek iyzico iframe içeriği burada olacak '
                f'(token={fake_token}) -->'
            ),
            'paymentPageUrl': f'https://sandbox-mock.local/checkout/{fake_token}',
            'tokenExpireTime': 1800,
        }

    @classmethod
    def handle_webhook(cls, payload, signature_header):
        """
        iyzico'dan gelen webhook'u isler. HPP (CheckoutForm) formati
        varsayilir, cunku create_checkout CheckoutFormInitialize kullaniyor.

        Resmi sema (docs.iyzico.com/en/advanced/webhook, HPP format):
            key = SECRET_KEY + iyziEventType + iyziPaymentId + token
                  + paymentConversationId + status
            signature = HEX(HMAC_SHA256(key, SECRET_KEY))
        X-Iyz-Signature ve X-Iyz-Signature-V2 artik desteklenmiyor, sadece
        X-IYZ-SIGNATURE-V3 kullanilmali.

        ONEMLI: X-IYZ-SIGNATURE-V3 gonderimi hesapta varsayilan olarak KAPALI.
        Sandbox/prod hesabinda aktif etmek icin entegrasyon@iyzico.com ile
        iletisime gecilmesi gerekiyor (bkz. iyzico resmi dokumantasyonu).

        Args:
            payload: webhook body'sinin parse edilmis hali (dict).
            signature_header: X-IYZ-SIGNATURE-V3 header degeri.

        Returns:
            Guncellenen Payment kaydi.

        Raises:
            PaymentServiceError: imza dogrulanamazsa veya eslesen Payment
                bulunamazsa.
        """
        if not cls._verify_webhook_signature(payload, signature_header):
            logger.warning(
                'iyzico webhook imza dogrulamasi basarisiz. paymentConversationId=%s',
                payload.get('paymentConversationId'),
            )
            raise PaymentServiceError('Gecersiz webhook imzasi.')

        conversation_id = payload.get('paymentConversationId')
        iyzico_status = payload.get('status')

        try:
            payment = Payment.objects.get(transaction_id=conversation_id)
        except Payment.DoesNotExist as exc:
            raise PaymentServiceError(
                f'Webhook icin eslesen Payment bulunamadi: paymentConversationId={conversation_id}'
            ) from exc

        payment.raw_response = {**(payment.raw_response or {}), 'webhook': payload}

        if iyzico_status == 'SUCCESS':
            payment.status = Payment.Status.COMPLETED
            membership = payment.membership
            membership.status = 'active'
            membership.save(update_fields=['status'])
        elif iyzico_status == 'FAILURE':
            payment.status = Payment.Status.FAILED

        payment.save()
        logger.info(
            'iyzico webhook islendi: payment_id=%s, status=%s', payment.id, payment.status
        )
        return payment

    @classmethod
    def _verify_webhook_signature(cls, payload, signature_header):
        """
        HPP format imza dogrulamasi. Mock modda (secret key yokken) hicbir
        imza guvenilir sayilmaz — her zaman False doner.
        """
        if cls.is_mock_mode() or not signature_header:
            return False

        secret_key = settings.IYZICO_SECRET_KEY
        key = (
            secret_key
            + str(payload.get('iyziEventType', ''))
            + str(payload.get('iyziPaymentId', ''))
            + str(payload.get('token', ''))
            + str(payload.get('paymentConversationId', ''))
            + str(payload.get('status', ''))
        )
        computed = hmac.new(secret_key.encode('utf-8'), key.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature_header)

    @classmethod
    def refund(cls, payment):
        """İskelet — Sprint 2 backlog: refund akışı."""
        raise NotImplementedError('Refund akışı Sprint 2 backlog\'ta, henüz implement edilmedi.')
