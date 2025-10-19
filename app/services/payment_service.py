"""
Stripe payment service for handling subscriptions and payments
"""
import stripe
from typing import Dict, List, Optional, Any
from decimal import Decimal
from loguru import logger
from app.config import settings

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key

class StripePaymentService:
    """
    Service for handling Stripe payments and subscriptions
    """
    
    def __init__(self):
        self.stripe = stripe
        
    async def create_customer(self, user_id: int, email: str, name: str = None) -> Dict[str, Any]:
        """
        Create a Stripe customer for a user
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    'user_id': str(user_id),
                    'platform': 'quantpulse'
                }
            )
            
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return {
                'success': True,
                'customer_id': customer.id,
                'customer': customer
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_subscription(self, customer_id: str, price_id: str, 
                                 trial_period_days: int = None) -> Dict[str, Any]:
        """
        Create a subscription for a customer
        """
        try:
            subscription_data = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'metadata': {
                    'platform': 'quantpulse'
                },
                'expand': ['latest_invoice.payment_intent']
            }
            
            if trial_period_days:
                subscription_data['trial_period_days'] = trial_period_days
            
            subscription = stripe.Subscription.create(**subscription_data)
            
            logger.info(f"Created subscription {subscription.id} for customer {customer_id}")
            return {
                'success': True,
                'subscription': subscription,
                'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice.payment_intent else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cancel_subscription(self, subscription_id: str, 
                                 cancel_at_period_end: bool = True) -> Dict[str, Any]:
        """
        Cancel a subscription
        """
        try:
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Cancelled subscription {subscription_id}")
            return {
                'success': True,
                'subscription': subscription
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def update_subscription(self, subscription_id: str, 
                                 new_price_id: str) -> Dict[str, Any]:
        """
        Update a subscription to a new plan
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations'
            )
            
            updated_subscription = stripe.Subscription.retrieve(subscription_id)
            
            logger.info(f"Updated subscription {subscription_id} to price {new_price_id}")
            return {
                'success': True,
                'subscription': updated_subscription
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_payment_method(self, customer_id: str, 
                                   payment_method_id: str) -> Dict[str, Any]:
        """
        Attach a payment method to a customer
        """
        try:
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
            
            logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
            return {
                'success': True,
                'payment_method': payment_method
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_setup_intent(self, customer_id: str) -> Dict[str, Any]:
        """
        Create a setup intent for saving payment methods
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                usage='off_session'
            )
            
            logger.info(f"Created setup intent {setup_intent.id} for customer {customer_id}")
            return {
                'success': True,
                'setup_intent': setup_intent,
                'client_secret': setup_intent.client_secret
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to create setup intent: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_customer_subscriptions(self, customer_id: str) -> Dict[str, Any]:
        """
        Get all subscriptions for a customer
        """
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='all',
                expand=['data.default_payment_method']
            )
            
            return {
                'success': True,
                'subscriptions': subscriptions.data
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get customer subscriptions: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_invoice_preview(self, customer_id: str, 
                                 subscription_id: str, 
                                 new_price_id: str) -> Dict[str, Any]:
        """
        Preview invoice for subscription changes
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            invoice = stripe.Invoice.upcoming(
                customer=customer_id,
                subscription=subscription_id,
                subscription_items=[{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }],
            )
            
            return {
                'success': True,
                'invoice': invoice
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Failed to preview invoice: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def handle_webhook(self, payload: str, signature: str) -> Dict[str, Any]:
        """
        Handle Stripe webhooks
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, 
                signature, 
                settings.stripe_webhook_secret
            )
            
            logger.info(f"Received Stripe webhook: {event['type']}")
            
            return {
                'success': True,
                'event': event
            }
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            return {
                'success': False,
                'error': 'Invalid payload'
            }
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return {
                'success': False,
                'error': 'Invalid signature'
            }


class PaymentPlanManager:
    """
    Manager for subscription plans and pricing
    """
    
    # Define subscription plans
    PLANS = {
        'basic': {
            'name': 'Basic Plan',
            'price_monthly': 29.99,
            'price_yearly': 299.99,
            'features': [
                '5 active strategies',
                '100 alerts per day',
                '1 broker connection',
                'Basic analytics',
                'Email support'
            ],
            'stripe_price_id_monthly': settings.basic_plan_price_id,
            'stripe_price_id_yearly': None,  # Add when created
            'max_strategies': 5,
            'max_alerts_per_day': 100,
            'max_brokers': 1
        },
        'plus': {
            'name': 'Plus Plan', 
            'price_monthly': 79.99,
            'price_yearly': 799.99,
            'features': [
                '25 active strategies',
                '1000 alerts per day',
                '3 broker connections',
                'Advanced analytics',
                'Priority support',
                'Strategy backtesting'
            ],
            'stripe_price_id_monthly': settings.plus_plan_price_id,
            'stripe_price_id_yearly': None,
            'max_strategies': 25,
            'max_alerts_per_day': 1000,
            'max_brokers': 3
        },
        'ultra': {
            'name': 'Ultra Plan',
            'price_monthly': 199.99,
            'price_yearly': 1999.99,
            'features': [
                'Unlimited strategies',
                'Unlimited alerts',
                'Unlimited broker connections',
                'Real-time analytics',
                'Phone + chat support',
                'Advanced backtesting',
                'Custom indicators',
                'API access'
            ],
            'stripe_price_id_monthly': settings.ultra_plan_price_id,
            'stripe_price_id_yearly': None,
            'max_strategies': -1,  # -1 = unlimited
            'max_alerts_per_day': -1,
            'max_brokers': -1
        }
    }
    
    @classmethod
    def get_plan(cls, plan_name: str) -> Optional[Dict[str, Any]]:
        """Get plan details by name"""
        return cls.PLANS.get(plan_name.lower())
    
    @classmethod
    def get_all_plans(cls) -> Dict[str, Any]:
        """Get all available plans"""
        return cls.PLANS
    
    @classmethod
    def get_plan_limits(cls, plan_name: str) -> Dict[str, int]:
        """Get limits for a specific plan"""
        plan = cls.get_plan(plan_name)
        if not plan:
            return {'max_strategies': 0, 'max_alerts_per_day': 0, 'max_brokers': 0}
        
        return {
            'max_strategies': plan['max_strategies'],
            'max_alerts_per_day': plan['max_alerts_per_day'],
            'max_brokers': plan['max_brokers']
        }