import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreateRequest } from '../hooks/useRequests';
import {
  ArrowLeftIcon,
  UserIcon,
  EnvelopeIcon,
  DocumentTextIcon,
  FlagIcon,
  SparklesIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';

export default function NewRequest() {
  const navigate = useNavigate();
  const createRequest = useCreateRequest();

  const [formData, setFormData] = useState({
    requester_name: '',
    requester_email: '',
    requester_phone: '',
    requester_organization: '',
    description: '',
    request_type: 'standard',
    priority: 'medium',
    delivery_method: 'email',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [currentStep, setCurrentStep] = useState(1);

  const handleChange = (
    e: React.ChangeEvent<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.requester_name.trim()) {
      newErrors.requester_name = 'Requester name is required';
    }

    if (!formData.requester_email.trim()) {
      newErrors.requester_email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.requester_email)) {
      newErrors.requester_email = 'Invalid email format';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Request description is required';
    } else if (formData.description.trim().length < 20) {
      newErrors.description = 'Description must be at least 20 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) {
      return;
    }

    try {
      const result = await createRequest.mutateAsync(formData);
      navigate(`/requests/${result.id}`);
    } catch (error) {
      console.error('Failed to create request:', error);
    }
  };

  const nextStep = () => {
    if (currentStep === 1) {
      const step1Errors: Record<string, string> = {};
      if (!formData.requester_name.trim()) {
        step1Errors.requester_name = 'Requester name is required';
      }
      if (!formData.requester_email.trim()) {
        step1Errors.requester_email = 'Email is required';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.requester_email)) {
        step1Errors.requester_email = 'Invalid email format';
      }
      if (Object.keys(step1Errors).length > 0) {
        setErrors(step1Errors);
        return;
      }
    }
    setCurrentStep((prev) => prev + 1);
  };

  const prevStep = () => setCurrentStep((prev) => prev - 1);

  const steps = [
    { number: 1, title: 'Requester Info', icon: UserIcon },
    { number: 2, title: 'Request Details', icon: DocumentTextIcon },
    { number: 3, title: 'Settings', icon: FlagIcon },
  ];

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/requests')}
          className="p-2.5 text-navy-400 hover:text-white hover:bg-navy-800 rounded-xl transition-colors"
        >
          <ArrowLeftIcon className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white">
            New PIA Request
          </h1>
          <p className="text-navy-400 mt-1">
            Create a new public information request
          </p>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6">
        <div className="flex items-center justify-between relative">
          {/* Progress Line */}
          <div className="absolute top-6 left-0 right-0 h-0.5 bg-navy-700">
            <div
              className="h-full bg-gradient-to-r from-tronas-500 to-tronas-400 transition-all duration-500"
              style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
            />
          </div>

          {steps.map((step) => {
            const Icon = step.icon;
            const isCompleted = currentStep > step.number;
            const isCurrent = currentStep === step.number;

            return (
              <div key={step.number} className="relative flex flex-col items-center z-10">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300 ${
                    isCompleted
                      ? 'bg-tronas-500 text-white shadow-glow'
                      : isCurrent
                      ? 'bg-tronas-500/20 text-tronas-400 border-2 border-tronas-500'
                      : 'bg-navy-800 text-navy-500 border border-navy-700'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircleIcon className="w-6 h-6" />
                  ) : (
                    <Icon className="w-6 h-6" />
                  )}
                </div>
                <span
                  className={`mt-2 text-sm font-medium ${
                    isCurrent ? 'text-tronas-400' : isCompleted ? 'text-white' : 'text-navy-500'
                  }`}
                >
                  {step.title}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <div className="bg-navy-900/50 backdrop-blur-xl rounded-2xl border border-navy-800 p-6 md:p-8">
          {/* Step 1: Requester Information */}
          {currentStep === 1 && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-tronas-500/20">
                  <UserIcon className="w-5 h-5 text-tronas-400" />
                </div>
                <h2 className="text-xl font-semibold text-white">Requester Information</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Full Name <span className="text-danger-500">*</span>
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-500" />
                    <input
                      type="text"
                      name="requester_name"
                      value={formData.requester_name}
                      onChange={handleChange}
                      className={`w-full pl-12 pr-4 py-3 bg-navy-800/50 border rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 transition-all ${
                        errors.requester_name ? 'border-danger-500' : 'border-navy-700 focus:border-tronas-500'
                      }`}
                      placeholder="John Doe"
                    />
                  </div>
                  {errors.requester_name && (
                    <p className="text-danger-400 text-sm mt-2">{errors.requester_name}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Email Address <span className="text-danger-500">*</span>
                  </label>
                  <div className="relative">
                    <EnvelopeIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-navy-500" />
                    <input
                      type="email"
                      name="requester_email"
                      value={formData.requester_email}
                      onChange={handleChange}
                      className={`w-full pl-12 pr-4 py-3 bg-navy-800/50 border rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 transition-all ${
                        errors.requester_email ? 'border-danger-500' : 'border-navy-700 focus:border-tronas-500'
                      }`}
                      placeholder="john.doe@example.com"
                    />
                  </div>
                  {errors.requester_email && (
                    <p className="text-danger-400 text-sm mt-2">{errors.requester_email}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    name="requester_phone"
                    value={formData.requester_phone}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                    placeholder="(210) 555-0123"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Organization
                  </label>
                  <input
                    type="text"
                    name="requester_organization"
                    value={formData.requester_organization}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                    placeholder="Company or organization name"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Request Details */}
          {currentStep === 2 && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-tronas-500/20">
                  <DocumentTextIcon className="w-5 h-5 text-tronas-400" />
                </div>
                <h2 className="text-xl font-semibold text-white">Request Details</h2>
              </div>

              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  Request Description <span className="text-danger-500">*</span>
                </label>
                <textarea
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  rows={8}
                  className={`w-full px-4 py-3 bg-navy-800/50 border rounded-xl text-white placeholder:text-navy-500 focus:outline-none focus:ring-2 focus:ring-tronas-500/50 transition-all resize-none ${
                    errors.description ? 'border-danger-500' : 'border-navy-700 focus:border-tronas-500'
                  }`}
                  placeholder="Please describe the records you are requesting. Be as specific as possible including dates, names, departments, and any other relevant details..."
                />
                {errors.description && (
                  <p className="text-danger-400 text-sm mt-2">{errors.description}</p>
                )}
                <p className="text-navy-500 text-sm mt-2">
                  {formData.description.length} characters
                </p>
              </div>

              <div className="bg-navy-800/30 rounded-xl p-4 border border-navy-700">
                <div className="flex items-start gap-3">
                  <SparklesIcon className="w-5 h-5 text-tronas-400 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-medium text-white">AI-Powered Processing</h4>
                    <p className="text-sm text-navy-400 mt-1">
                      Our AI will analyze your request and automatically identify relevant records,
                      classify documents, and flag any exemptions under the Texas Public Information Act.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Settings */}
          {currentStep === 3 && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-tronas-500/20">
                  <FlagIcon className="w-5 h-5 text-tronas-400" />
                </div>
                <h2 className="text-xl font-semibold text-white">Request Settings</h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Request Type
                  </label>
                  <select
                    name="request_type"
                    value={formData.request_type}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                  >
                    <option value="standard" className="bg-navy-900">Standard Request</option>
                    <option value="expedited" className="bg-navy-900">Expedited Request</option>
                    <option value="recurring" className="bg-navy-900">Recurring Request</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Priority
                  </label>
                  <select
                    name="priority"
                    value={formData.priority}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                  >
                    <option value="low" className="bg-navy-900">Low</option>
                    <option value="medium" className="bg-navy-900">Medium</option>
                    <option value="high" className="bg-navy-900">High</option>
                    <option value="urgent" className="bg-navy-900">Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-navy-300 mb-2">
                    Preferred Delivery Method
                  </label>
                  <select
                    name="delivery_method"
                    value={formData.delivery_method}
                    onChange={handleChange}
                    className="w-full px-4 py-3 bg-navy-800/50 border border-navy-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-tronas-500/50 focus:border-tronas-500 transition-all"
                  >
                    <option value="email" className="bg-navy-900">Email</option>
                    <option value="portal" className="bg-navy-900">Portal Download</option>
                    <option value="mail" className="bg-navy-900">Physical Mail</option>
                    <option value="pickup" className="bg-navy-900">In-Person Pickup</option>
                  </select>
                </div>
              </div>

              {/* Summary */}
              <div className="bg-navy-800/30 rounded-xl p-6 border border-navy-700 mt-6">
                <h4 className="text-sm font-semibold text-white mb-4 uppercase tracking-wide">Request Summary</h4>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-navy-400">Requester:</span>
                    <span className="text-white font-medium">{formData.requester_name || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-navy-400">Email:</span>
                    <span className="text-white">{formData.requester_email || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-navy-400">Type:</span>
                    <span className="text-white capitalize">{formData.request_type.replace('_', ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-navy-400">Priority:</span>
                    <span className={`font-medium capitalize ${
                      formData.priority === 'urgent' ? 'text-danger-400' :
                      formData.priority === 'high' ? 'text-warning-400' :
                      'text-white'
                    }`}>{formData.priority}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center mt-8 pt-6 border-t border-navy-700">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={prevStep}
                className="px-6 py-2.5 text-navy-400 hover:text-white font-medium transition-colors"
              >
                Back
              </button>
            ) : (
              <button
                type="button"
                onClick={() => navigate('/requests')}
                className="px-6 py-2.5 text-navy-400 hover:text-white font-medium transition-colors"
              >
                Cancel
              </button>
            )}

            {currentStep < 3 ? (
              <button
                type="button"
                onClick={nextStep}
                className="px-6 py-2.5 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white rounded-xl font-medium shadow-glow transition-all duration-200"
              >
                Continue
              </button>
            ) : (
              <button
                type="submit"
                disabled={createRequest.isPending}
                className="px-6 py-2.5 bg-gradient-to-r from-tronas-500 to-tronas-600 hover:from-tronas-400 hover:to-tronas-500 text-white rounded-xl font-medium shadow-glow transition-all duration-200 disabled:opacity-50"
              >
                {createRequest.isPending ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Creating...
                  </span>
                ) : (
                  'Create Request'
                )}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
