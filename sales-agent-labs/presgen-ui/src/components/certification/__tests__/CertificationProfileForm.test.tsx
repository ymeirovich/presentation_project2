import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import CertificationProfileForm from '../CertificationProfileForm';
import { CertificationAPI } from '@/lib/certification-api';

// Mock the API
vi.mock('@/lib/certification-api', () => ({
  CertificationAPI: {
    create: vi.fn(),
    update: vi.fn(),
  },
}));

// Mock react-hook-form for testing
vi.mock('react-hook-form', async () => {
  const actual = await vi.importActual('react-hook-form');
  return {
    ...actual,
    useForm: () => ({
      register: () => ({}),
      control: {},
      handleSubmit: (fn: any) => (e: any) => {
        e.preventDefault();
        fn({
          name: 'Test Certification',
          version: '1.0',
          exam_domains: [
            {
              name: 'Domain 1',
              weight_percentage: 50,
              subdomains: ['Sub 1'],
              skills_measured: ['Skill 1']
            },
            {
              name: 'Domain 2',
              weight_percentage: 50,
              subdomains: ['Sub 2'],
              skills_measured: ['Skill 2']
            }
          ]
        });
      },
      watch: () => ({
        name: 'Test Certification',
        version: '1.0',
        exam_domains: [
          {
            name: 'Domain 1',
            weight_percentage: 50,
            subdomains: ['Sub 1'],
            skills_measured: ['Skill 1']
          },
          {
            name: 'Domain 2',
            weight_percentage: 50,
            subdomains: ['Sub 2'],
            skills_measured: ['Skill 2']
          }
        ]
      }),
      setValue: vi.fn(),
      formState: { errors: {}, isValid: true }
    }),
    useFieldArray: () => ({
      fields: [
        {
          id: '1',
          name: 'Domain 1',
          weight_percentage: 50,
          subdomains: ['Sub 1'],
          skills_measured: ['Skill 1']
        }
      ],
      append: vi.fn(),
      remove: vi.fn()
    })
  };
});

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

describe('CertificationProfileForm', () => {
  const mockOnSave = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders create form correctly', () => {
    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Create Certification Profile')).toBeInTheDocument();
    expect(screen.getByText('Configure assessment domains and knowledge requirements')).toBeInTheDocument();
  });

  it('renders edit form with profile data', () => {
    const mockProfile = {
      id: '123',
      name: 'AWS Solutions Architect',
      version: '2023',
      exam_domains: [
        {
          name: 'Design Secure Architectures',
          weight_percentage: 30,
          subdomains: ['Security', 'Compliance'],
          skills_measured: ['IAM', 'Encryption']
        }
      ],
      knowledge_base_path: 'kb/aws',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    render(
      <CertificationProfileForm
        profile={mockProfile}
        mode="edit"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Edit Certification Profile')).toBeInTheDocument();
  });

  it('shows completion percentage', () => {
    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Should show some completion percentage
    expect(screen.getByText(/\d+% Complete/)).toBeInTheDocument();
  });

  it('handles form submission for create mode', async () => {
    const mockCreatedProfile = {
      id: '123',
      name: 'Test Certification',
      version: '1.0',
      exam_domains: [],
      knowledge_base_path: 'kb/test',
      created_at: '2023-01-01T00:00:00Z',
      updated_at: '2023-01-01T00:00:00Z'
    };

    (CertificationAPI.create as any).mockResolvedValue(mockCreatedProfile);

    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const submitButton = screen.getByRole('button', { name: /create profile/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(CertificationAPI.create).toHaveBeenCalled();
      expect(mockOnSave).toHaveBeenCalledWith(mockCreatedProfile);
    });
  });

  it('shows domain weight validation', () => {
    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    // Should show weight total
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('handles cancel action', () => {
    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('shows auto-balance button for domain weights', () => {
    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByRole('button', { name: /auto-balance/i })).toBeInTheDocument();
  });

  it('displays form sections correctly', () => {
    render(
      <CertificationProfileForm
        mode="create"
        onSave={mockOnSave}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Basic Information')).toBeInTheDocument();
    expect(screen.getByText('Exam Domains')).toBeInTheDocument();
    expect(screen.getByText('Assessment Template (Optional)')).toBeInTheDocument();
  });
});